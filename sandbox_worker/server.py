"""
HTTP API Service for the PrepFly Isolated Sandbox Worker.
Provides secure /execute, /health, /metrics, and /audit/recent endpoints with
HMAC authentication, per-user/per-IP quotas, queue dispatch, and audit logging.
"""

import hmac
import os
import shutil
import time
import uuid
from flask import Flask, request, jsonify, Response


from config import config
from runner import runner
from queue_manager import queue_manager
from quota import quota_manager
from audit import audit_logger

app = Flask(__name__)


def validate_sandbox_startup():
    """
    Validates security boundaries at worker startup.
    In production (ENVIRONMENT=production), strictly refuses to start unless
    the isolation mode is container or microvm, and auto must never fall back to process mode.
    """
    is_prod = (
        os.getenv("ENVIRONMENT", "").lower() == "production"
        or os.getenv("FLASK_ENV", "").lower() == "production"
        or getattr(config, "ENVIRONMENT", "").lower() == "production"
    )
    if is_prod:
        active_mode = runner.get_isolation_mode()
        if active_mode not in ("container", "microvm"):
            raise RuntimeError(
                f"Production security violation: Sandbox worker refused to start with weak isolation '{active_mode}'. "
                f"Must be 'container' or 'microvm'."
            )
        secret = getattr(config, "SECRET", "") or os.getenv("ISOLATED_SANDBOX_SECRET", "")
        if not secret or secret == "prepfly-sandbox-dev-secret-32-chars-long-minimum" or len(secret) < 32:
            raise RuntimeError(
                "Production security violation: ISOLATED_SANDBOX_SECRET must be configured with a strong, "
                "unique secret (minimum 32 characters) in production mode."
            )
        print(f"[PREPFLY SANDBOX WORKER] Production startup verified with strong isolation: '{active_mode}'")


validate_sandbox_startup()


def _verify_auth(req) -> bool:
    """Verifies X-Sandbox-Secret using constant-time string comparison."""
    is_prod = (
        os.getenv("ENVIRONMENT", "").lower() == "production"
        or os.getenv("FLASK_ENV", "").lower() == "production"
        or getattr(config, "ENVIRONMENT", "").lower() == "production"
    )
    if is_prod and (not config.SECRET or config.SECRET == "prepfly-sandbox-dev-secret-32-chars-long-minimum"):
        return False
    if not config.SECRET:
        # If no secret configured in dev mode, allow execution with notice
        return True
    provided_secret = req.headers.get("X-Sandbox-Secret", "")
    return hmac.compare_digest(provided_secret.encode("utf-8"), config.SECRET.encode("utf-8"))



@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint reporting toolchain availability, queue load, and worker health."""
    toolchains = {
        "python": shutil.which("python3") is not None or shutil.which("python") is not None,
        "javascript": shutil.which("node") is not None,
        "cpp": shutil.which("g++") is not None,
        "c": shutil.which("gcc") is not None,
        "java": shutil.which("javac") is not None and shutil.which("java") is not None
    }
    queue_metrics = queue_manager.get_metrics()
    quota_stats = quota_manager.get_stats()

    return jsonify({
        "status": "healthy",
        "service": "prepfly-sandbox-worker",
        "isolation_mode": runner.get_isolation_mode(),
        "active_jobs": queue_manager.active_jobs_count,
        "total_processed": queue_manager.total_processed,
        "queue": queue_metrics,
        "quotas": {
            "per_user_minute": config.USER_QUOTA_PER_MINUTE,
            "per_user_hour": config.USER_QUOTA_PER_HOUR,
            "max_concurrent_user_jobs": config.USER_MAX_CONCURRENT_JOBS,
            "guest_minute": config.GUEST_QUOTA_PER_MINUTE,
            "ip_minute": config.RATE_LIMIT_PER_MINUTE,
            "stats": quota_stats
        },
        "toolchains": toolchains,
        "limits": {
            "cpu_time_sec": config.CPU_TIME_LIMIT_SECONDS,
            "wall_time_sec": config.WALL_TIME_LIMIT_SECONDS,
            "memory_mb": config.MEMORY_LIMIT_BYTES // (1024 * 1024),
            "max_processes": config.MAX_PROCESSES,
            "max_output_kb": config.MAX_OUTPUT_BYTES // 1024,
            "max_code_size_kb": config.MAX_CODE_SIZE_BYTES // 1024
        }
    }), 200


@app.route("/metrics", methods=["GET"])
def metrics_endpoint():
    """Provides queue and quota telemetry metrics."""
    return jsonify({
        "queue": queue_manager.get_metrics(),
        "quotas": quota_manager.get_stats(),
        "isolation_mode": runner.get_isolation_mode()
    }), 200


@app.route("/audit/recent", methods=["GET"])
def recent_audit_logs():
    """Returns recent structured audit events (authenticated with X-Sandbox-Secret)."""
    if not _verify_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    limit = min(100, max(1, int(request.args.get("limit", 20))))
    return jsonify({"events": audit_logger.get_recent_logs(limit=limit)}), 200


@app.route("/execute", methods=["POST"])
def execute_code():
    """
    Executes submitted code within an isolated sandbox environment.
    Strictly verifies authorization, enforces per-user quotas, and audits invocation.
    """
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
    job_id = f"job-{uuid.uuid4().hex[:12]}"

    # 1. Authenticate caller
    if not _verify_auth(request):
        audit_logger.log_event(
            event_type="AUTH_FAILURE",
            job_id=job_id,
            client_ip=client_ip,
            language="unknown",
            problem_id="unknown",
            status="unauthorized",
            error="Invalid or missing X-Sandbox-Secret"
        )
        return jsonify({"error": "Unauthorized: Invalid or missing X-Sandbox-Secret"}), 401

    # 2. Parse and validate JSON payload
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Bad Request: Request body must be valid JSON"}), 400

    user_id = data.get("user_id") or request.headers.get("X-User-Id")
    if user_id:
        user_id = str(user_id)[:64]

    language = str(data.get("language", "")).strip().lower()
    code = data.get("code", "")
    problem_id = str(data.get("problem_id", "unspecified"))[:64]
    test_cases = data.get("test_cases", [])

    if not language:
        return jsonify({"error": "Bad Request: 'language' parameter is required"}), 400
    if not code or not isinstance(code, str):
        return jsonify({"error": "Bad Request: 'code' parameter must be a non-empty string"}), 400
    if not isinstance(test_cases, list) or len(test_cases) == 0:
        return jsonify({"error": "Bad Request: 'test_cases' parameter must be a non-empty list"}), 400

    if len(code.encode("utf-8")) > config.MAX_CODE_SIZE_BYTES:
        return jsonify({"error": f"Payload Too Large: Code exceeds maximum size of {config.MAX_CODE_SIZE_BYTES} bytes"}), 413

    # Limit test cases to avoid denial-of-service
    capped_cases = test_cases[:50]

    # 3. Check and acquire quota
    allowed, reason, retry_after = quota_manager.acquire(user_id=user_id, client_ip=client_ip)
    if not allowed:
        event_name = "USER_QUOTA_EXCEEDED" if user_id else "RATE_LIMITED"
        audit_logger.log_event(
            event_type=event_name,
            job_id=job_id,
            client_ip=client_ip,
            user_id=user_id,
            language=language,
            problem_id=problem_id,
            status="rate_limited",
            error=reason
        )
        resp = jsonify({
            "error": f"Too Many Requests: {reason}",
            "retry_after": retry_after
        })
        resp.status_code = 429
        resp.headers["Retry-After"] = str(retry_after)
        return resp

    # 4. Dispatch job to bounded queue with guaranteed quota release
    start_time = time.perf_counter()
    try:
        result = queue_manager.dispatch(
            runner.run_submission,
            language,
            code,
            capped_cases,
            problem_id
        )
    finally:
        quota_manager.release(user_id=user_id, client_ip=client_ip)

    total_duration_ms = (time.perf_counter() - start_time) * 1000.0
    effective_isolation = result.get("isolation_mode", runner.get_isolation_mode())

    # 5. Determine overall audit status
    overall_status = "success"
    error_msg = None
    if "error" in result:
        overall_status = "error"
        error_msg = result["error"]
    elif "results" in result:
        any_failed = any(not r.get("passed") for r in result["results"])
        any_error = any(r.get("status") in ("runtime_error", "compilation_error", "time_limit_exceeded", "memory_limit_exceeded") for r in result["results"])
        if any_error:
            overall_status = "error"
        elif any_failed:
            overall_status = "failed_cases"

    # 6. Structured audit log
    audit_logger.log_event(
        event_type="CODE_EXECUTION",
        job_id=job_id,
        client_ip=client_ip,
        user_id=user_id,
        isolation_mode=effective_isolation,
        language=language,
        problem_id=problem_id,
        status=overall_status,
        execution_time_ms=total_duration_ms,
        memory_kb=result.get("results", [{}])[0].get("mem_kb", 0.0) if result.get("results") else 0.0,
        error=error_msg,
        extra={"test_case_count": len(capped_cases)}
    )

    if "error" in result:
        status_code = result.get("status_code", 400)
        return jsonify(result), status_code

    return jsonify(result), 200


if __name__ == "__main__":
    print(f"[PREPFLY SANDBOX WORKER] Starting on {config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)
