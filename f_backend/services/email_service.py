"""
Unified, Non-Blocking Email Delivery Service for PrepFly.
Supports:
  - Resend HTTPS API (Port 443)
  - Environment-driven SMTP host, port, timeout, and TLS/SSL mode
  - Separate handling for authentication/permanent errors (no retry) vs transient network/4xx errors
  - Background delivery queue so core API operations never block on SMTP timeouts
  - Secret-safe structured logging and delivery status reporting
"""

import json
import logging
import os
import queue
import random
import smtplib
import socket
import ssl
import threading
import time
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("prepfly.email")

_EMAIL_QUEUE: queue.Queue = queue.Queue(maxsize=200)
_WORKER_LOCK = threading.Lock()
_WORKER_STARTED = False
_STATS_LOCK = threading.Lock()
_EMAIL_STATS: Dict[str, Any] = {
    "queued": 0,
    "sent": 0,
    "failed": 0,
    "last_transport": None,
    "last_error": None,
}


def _classify_smtp_exception(err: Exception) -> Tuple[str, bool]:
    """
    Returns (category, is_permanent).
    Auth errors and permanent 5xx recipient/sender rejections are never retried.
    """
    if isinstance(err, smtplib.SMTPAuthenticationError):
        return "auth_failed", True
    if isinstance(err, (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused)):
        return "recipient_rejected", True
    if isinstance(err, smtplib.SMTPResponseException):
        code = getattr(err, "smtp_code", 0) or 0
        if code == 535 or code in (530, 534):
            return "auth_failed", True
        if 500 <= code < 600:
            return f"smtp_{code}", True
        if 400 <= code < 500:
            return f"smtp_transient_{code}", False

    msg = str(err or "").lower()
    if any(tok in msg for tok in ("authentication failed", "invalid credentials", "username and password not accepted", "535")):
        return "auth_failed", True
    if any(tok in msg for tok in ("network is unreachable", "errno 101", "enetunreach", "connection refused", "econnrefused", "getaddrinfo", "name or service not known")):
        return "network_unreachable", True
    if isinstance(err, (TimeoutError, socket.timeout)) or "timed out" in msg or "timeout" in msg:
        return "timeout", False
    return type(err).__name__, False


def _resolve_ipv4_targets(smtp_server: str, port: int) -> List[str]:
    if not smtp_server:
        return []
    targets = [smtp_server]
    try:
        infos = socket.getaddrinfo(smtp_server, port, family=socket.AF_INET, type=socket.SOCK_STREAM)
        for info in infos:
            ip = info[4][0]
            if ip and ip not in targets:
                targets.insert(0, ip)
    except Exception:
        pass
    return targets[:2]


def _send_via_resend(to_email: str, subject: str, html_body: str, resend_api_key: str) -> Tuple[bool, str]:
    payload = json.dumps({
        "from": os.getenv("RESEND_FROM_EMAIL", "PrepFly <onboarding@resend.dev>"),
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        if resp.status in (200, 201):
            return True, f"resend_http_{resp.status}"
        return False, f"resend_unexpected_status_{resp.status}"


def _attempt_smtp_port(
    host: str,
    port: int,
    sender_email: str,
    sender_password: str,
    msg: MIMEMultipart,
    timeout_s: float = 5.0,
    use_ssl: Optional[bool] = None,
    use_tls: Optional[bool] = None,
) -> None:
    tls_context = ssl.create_default_context()
    ssl_mode = (port == 465) if use_ssl is None else use_ssl
    if ssl_mode:
        with smtplib.SMTP_SSL(host, port, timeout=timeout_s, context=tls_context) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=timeout_s) as server:
            server.ehlo()
            if True if use_tls is None else use_tls:
                server.starttls(context=tls_context)
                server.ehlo()
            server.login(sender_email, sender_password)
            server.send_message(msg)


def _parse_bool_env(name: str) -> Optional[bool]:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return None
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def send_email_with_status(
    to_email: str,
    subject: str,
    html_body: str,
    is_html: bool = True,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """
    Sends email across Resend HTTPS API or environment-driven SMTP with bounded retries,
    separate auth vs transient handling, and structured status without logging secrets.
    """
    if not to_email or "@" not in str(to_email):
        logger.warning("[EMAIL] Invalid recipient address omitted.")
        return {"ok": False, "transport": None, "error_type": "invalid_recipient", "retryable": False, "attempts": 0}

    recipient_domain = str(to_email).split("@")[-1]
    resend_api_key = os.getenv("RESEND_API_KEY", "").strip()
    if resend_api_key and not resend_api_key.startswith("re_prepfly_rotated"):
        try:
            ok, detail = _send_via_resend(to_email, subject, html_body, resend_api_key)
            if ok:
                with _STATS_LOCK:
                    _EMAIL_STATS["sent"] += 1
                    _EMAIL_STATS["last_transport"] = "resend"
                    _EMAIL_STATS["last_error"] = None
                logger.info("[EMAIL DELIVERED] transport=resend domain=%s detail=%s", recipient_domain, detail)
                return {"ok": True, "transport": "resend", "error_type": None, "retryable": False, "attempts": 1}
        except Exception as exc:
            logger.warning("[EMAIL NOTICE] transport=resend domain=%s error_type=%s", recipient_domain, type(exc).__name__)

    sender_email = (os.getenv("SMTP_EMAIL") or os.getenv("SMTP_USER") or os.getenv("SENDER_EMAIL") or "").strip()
    sender_password = (os.getenv("SMTP_PASSWORD") or os.getenv("SENDER_PASSWORD") or "").strip()
    smtp_server = (os.getenv("SMTP_HOST") or os.getenv("SMTP_SERVER") or "").strip()

    if not sender_email or not sender_password:
        logger.warning("[EMAIL SKIPPED] SMTP credentials unavailable for domain=%s", recipient_domain)
        with _STATS_LOCK:
            _EMAIL_STATS["failed"] += 1
            _EMAIL_STATS["last_error"] = "missing_smtp_credentials"
        return {"ok": False, "transport": None, "error_type": "missing_smtp_credentials", "retryable": False, "attempts": 0}

    try:
        preferred_port = int(os.getenv("SMTP_PORT", "465"))
    except ValueError:
        preferred_port = 465

    try:
        smtp_timeout = max(1.0, min(15.0, float(os.getenv("SMTP_TIMEOUT", "5.0"))))
    except ValueError:
        smtp_timeout = 5.0

    env_use_ssl = _parse_bool_env("SMTP_USE_SSL")
    env_use_tls = _parse_bool_env("SMTP_USE_TLS")

    msg = MIMEMultipart("alternative")
    msg["From"] = os.getenv("SMTP_FROM") or f"PrepFly <{sender_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html" if is_html else "plain"))

    port_order = [preferred_port]
    if env_use_ssl is None and env_use_tls is None:
        for fallback_port in (465, 587):
            if fallback_port not in port_order:
                port_order.append(fallback_port)

    last_err_label = "missing_smtp_host"
    last_retryable = False
    attempts_used = 0
    retry_budget = max(1, int(max_retries))

    for attempt in range(retry_budget):
        attempts_used = attempt + 1
        permanent_abort = False
        for port in port_order:
            hosts = _resolve_ipv4_targets(smtp_server, port)
            if not hosts:
                permanent_abort = True
                last_err_label = "missing_smtp_host"
                last_retryable = False
                break
            stop_port_fallback = False
            for host in hosts:
                try:
                    _attempt_smtp_port(
                        host,
                        port,
                        sender_email,
                        sender_password,
                        msg,
                        timeout_s=smtp_timeout,
                        use_ssl=env_use_ssl,
                        use_tls=env_use_tls,
                    )
                    transport = f"smtp_ssl_{port}" if (port == 465 if env_use_ssl is None else env_use_ssl) else f"smtp_starttls_{port}"
                    with _STATS_LOCK:
                        _EMAIL_STATS["sent"] += 1
                        _EMAIL_STATS["last_transport"] = transport
                        _EMAIL_STATS["last_error"] = None
                    logger.info("[EMAIL DELIVERED] transport=%s domain=%s attempt=%d", transport, recipient_domain, attempts_used)
                    return {"ok": True, "transport": transport, "error_type": None, "retryable": False, "attempts": attempts_used}
                except Exception as exc:
                    err_cat, is_permanent = _classify_smtp_exception(exc)
                    last_err_label = f"{err_cat}_port_{port}"
                    last_retryable = not is_permanent
                    logger.warning(
                        "[EMAIL RETRY NOTICE] port=%d domain=%s attempt=%d error_type=%s retryable=%s",
                        port,
                        recipient_domain,
                        attempts_used,
                        err_cat,
                        not is_permanent,
                    )
                    if is_permanent:
                        permanent_abort = True
                        stop_port_fallback = True
                        break
                    # If server already replied at SMTP protocol level (e.g. 421/450), retry this same port on next attempt rather than switching ports
                    if err_cat.startswith("smtp_transient_"):
                        stop_port_fallback = True
                        break
            if permanent_abort or stop_port_fallback:
                break

        if permanent_abort or attempt >= retry_budget - 1:
            break
        sleep_s = (0.25 * (2 ** attempt)) + random.uniform(0.0, 0.15)
        time.sleep(sleep_s)

    with _STATS_LOCK:
        _EMAIL_STATS["failed"] += 1
        _EMAIL_STATS["last_error"] = last_err_label
    logger.error("[EMAIL FAILED] domain=%s reason=%s attempts=%d", recipient_domain, last_err_label, attempts_used)
    return {
        "ok": False,
        "transport": None,
        "error_type": last_err_label,
        "retryable": last_retryable,
        "attempts": attempts_used,
    }


def send_email_sync(
    to_email: str,
    subject: str,
    html_body: str,
    is_html: bool = True,
    max_retries: int = 2,
) -> bool:
    """Backward-compatible boolean wrapper around `send_email_with_status`."""
    return bool(send_email_with_status(to_email, subject, html_body, is_html=is_html, max_retries=max_retries).get("ok"))


def _email_worker_loop() -> None:
    while True:
        item = _EMAIL_QUEUE.get()
        try:
            to_email, subject, body, is_html = item
            send_email_with_status(to_email, subject, body, is_html=is_html)
        except Exception as exc:
            logger.error("[EMAIL WORKER ERROR] error_type=%s", type(exc).__name__)
        finally:
            _EMAIL_QUEUE.task_done()


def _ensure_worker_started() -> None:
    global _WORKER_STARTED
    with _WORKER_LOCK:
        if not _WORKER_STARTED:
            t = threading.Thread(target=_email_worker_loop, name="prepfly-email-worker", daemon=True)
            t.start()
            _WORKER_STARTED = True


def enqueue_email(to_email: str, subject: str, body: str, is_html: bool = True) -> bool:
    """Queues an email asynchronously without blocking caller HTTP threads."""
    _ensure_worker_started()
    try:
        _EMAIL_QUEUE.put_nowait((to_email, subject, body, is_html))
        with _STATS_LOCK:
            _EMAIL_STATS["queued"] += 1
        return True
    except queue.Full:
        logger.warning("[EMAIL QUEUE FULL] Falling back to single synchronous attempt.")
        return send_email_sync(to_email, subject, body, is_html=is_html, max_retries=1)


def get_email_queue_stats() -> Dict[str, Any]:
    with _STATS_LOCK:
        stats = dict(_EMAIL_STATS)
    stats["pending_in_queue"] = _EMAIL_QUEUE.qsize()
    stats["worker_running"] = _WORKER_STARTED
    return stats
