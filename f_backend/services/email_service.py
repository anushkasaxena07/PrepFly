"""
Unified, Non-Blocking Email Delivery Service for PrepFly.
Supports:
  - Resend HTTPS API (Port 443)
  - SMTP_SSL (Port 465) and SMTP + STARTTLS (Port 587) with proper SSL context
  - Bounded retries with fast-fail on network unreachable / DNS failures
  - Background delivery queue so core API operations never block on SMTP timeouts
  - Safe logging with zero credential/secret exposure
"""

import json
import logging
import os
import queue
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
_EMAIL_STATS = {
    "queued": 0,
    "sent": 0,
    "failed": 0,
    "last_transport": None,
    "last_error": None,
}


def _is_fast_fail_network_error(err: Exception) -> bool:
    msg = str(err).lower()
    return any(
        tok in msg
        for tok in (
            "network is unreachable",
            "errno 101",
            "enetunreach",
            "connection refused",
            "econnrefused",
            "getaddrinfo",
            "name or service not known",
            "authentication failed",
            "535",
        )
    )


def _resolve_ipv4_targets(smtp_server: str, port: int) -> List[str]:
    targets = [smtp_server]
    try:
        infos = socket.getaddrinfo(smtp_server, port, family=socket.AF_INET, type=socket.SOCK_STREAM)
        for info in infos:
            ip = info[4][0]
            if ip and ip not in targets:
                targets.insert(0, ip)
    except Exception:
        pass
    return targets


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
) -> None:
    tls_context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, 465, timeout=timeout_s, context=tls_context) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=timeout_s) as server:
            server.ehlo()
            server.starttls(context=tls_context)
            server.ehlo()
            server.login(sender_email, sender_password)
            server.send_message(msg)


def send_email_sync(
    to_email: str,
    subject: str,
    html_body: str,
    is_html: bool = True,
    max_retries: int = 2,
) -> bool:
    """
    Sends email synchronously across Resend HTTPS API then configured SMTP ports (465 SSL / 587 STARTTLS)
    with bounded retries and credential-safe logging.
    """
    if not to_email or "@" not in str(to_email):
        logger.warning("[EMAIL] Invalid recipient address omitted.")
        return False

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
                return True
        except Exception as exc:
            logger.warning("[EMAIL NOTICE] transport=resend domain=%s error_type=%s", recipient_domain, type(exc).__name__)

    sender_email = (os.getenv("SMTP_EMAIL") or os.getenv("SMTP_USER") or os.getenv("SENDER_EMAIL") or "").strip()
    sender_password = (os.getenv("SMTP_PASSWORD") or os.getenv("SENDER_PASSWORD") or "").strip()
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()

    if not sender_email or not sender_password:
        logger.warning("[EMAIL SKIPPED] SMTP credentials unavailable for domain=%s", recipient_domain)
        with _STATS_LOCK:
            _EMAIL_STATS["failed"] += 1
            _EMAIL_STATS["last_error"] = "missing_smtp_credentials"
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"PrepFly <{sender_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html" if is_html else "plain"))

    try:
        preferred_port = int(os.getenv("SMTP_PORT", "465"))
    except ValueError:
        preferred_port = 465

    port_order = [preferred_port]
    for fallback_port in (465, 587):
        if fallback_port not in port_order:
            port_order.append(fallback_port)

    last_err_label = "unknown"
    for attempt in range(max(1, int(max_retries))):
        fast_fail = False
        for port in port_order:
            hosts = _resolve_ipv4_targets(smtp_server, port)
            for host in hosts:
                try:
                    _attempt_smtp_port(host, port, sender_email, sender_password, msg, timeout_s=5.0)
                    transport = f"smtp_ssl_465" if port == 465 else f"smtp_starttls_{port}"
                    with _STATS_LOCK:
                        _EMAIL_STATS["sent"] += 1
                        _EMAIL_STATS["last_transport"] = transport
                        _EMAIL_STATS["last_error"] = None
                    logger.info("[EMAIL DELIVERED] transport=%s domain=%s attempt=%d", transport, recipient_domain, attempt + 1)
                    return True
                except Exception as exc:
                    # Sanitize error message so secrets can never leak
                    err_type = type(exc).__name__
                    last_err_label = f"{err_type}_port_{port}"
                    logger.warning(
                        "[EMAIL RETRY NOTICE] port=%d domain=%s attempt=%d error_type=%s",
                        port, recipient_domain, attempt + 1, err_type
                    )
                    if _is_fast_fail_network_error(exc):
                        fast_fail = True
                        break
            if fast_fail:
                break

        if fast_fail or attempt >= max_retries - 1:
            break
        time.sleep(0.25 * (2 ** attempt))

    with _STATS_LOCK:
        _EMAIL_STATS["failed"] += 1
        _EMAIL_STATS["last_error"] = last_err_label
    logger.error("[EMAIL FAILED] domain=%s reason=%s", recipient_domain, last_err_label)
    return False


def _email_worker_loop() -> None:
    while True:
        item = _EMAIL_QUEUE.get()
        try:
            to_email, subject, body, is_html = item
            send_email_sync(to_email, subject, body, is_html=is_html)
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

