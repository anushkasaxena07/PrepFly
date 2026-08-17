import os
import time
import logging
import datetime
from flask import request, g

logger = logging.getLogger("interviewsystem")

_sentry_initialized = False

def setup_logging_and_sentry(app=None):
    """Configures structured Python logging and initializes Sentry SDK if SENTRY_DSN is provided."""
    global _sentry_initialized

    # 1. Configure Python Logging Format & Level
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    date_format = "%Y-%m-%dT%H:%M:%S%z"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers if re-initialized
    for handler in root_logger.handlers:
        handler.setFormatter(logging.Formatter(log_format, date_format))

    logger.info(f"Structured logging initialized at level: {log_level_name}")

    # 2. Sentry Initialization
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            from sentry_sdk.integrations.logging import LoggingIntegration

            traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0"))
            profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "1.0"))
            environment = os.getenv("FLASK_ENV", "production")

            sentry_logging = LoggingIntegration(
                level=logging.INFO,        # Capture info and above as breadcrumbs
                event_level=logging.ERROR   # Send errors as events
            )

            integrations = [sentry_logging]
            if app:
                integrations.append(FlaskIntegration())

            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=integrations,
                send_default_pii=True,
                enable_logs=True,
                traces_sample_rate=traces_sample_rate,
                profiles_sample_rate=profiles_sample_rate,
                profile_lifecycle="trace",
                environment=environment
            )
            _sentry_initialized = True
            logger.info(f"Sentry SDK initialized with tracing, profiling & log integration for environment: '{environment}'.")
        except Exception as e:
            logger.error(f"Failed to initialize Sentry SDK: {e}")
            _sentry_initialized = False
    else:
        logger.info("SENTRY_DSN is not set. Sentry error tracking is disabled.")
        _sentry_initialized = False

    # 3. Attach Flask Request Middleware if app is provided
    if app:
        @app.before_request
        def log_request_start():
            g.start_time = time.time()
            if request.path != "/health":
                logger.info(f"--> [REQ] {request.method} {request.path} from {request.remote_addr}")

        @app.after_request
        def log_request_end(response):
            if hasattr(g, "start_time"):
                duration_ms = round((time.time() - g.start_time) * 1000, 2)
            else:
                duration_ms = 0.0
            
            if request.path != "/health":
                logger.info(f"<-- [RES] {request.method} {request.path} - {response.status_code} ({duration_ms}ms)")
            return response

def is_sentry_active():
    """Returns whether Sentry integration is currently active."""
    return _sentry_initialized

def check_health(supabase_client=None):
    """
    Performs system health checks including database latency and status.
    Returns structured dict suitable for /health endpoint JSON response.
    """
    db_health = {"status": "unknown"}
    is_healthy = True

    if supabase_client:
        start_time = time.time()
        try:
            # Query a standard table or execute lightweight check
            supabase_client.table("users").select("id", count="exact").limit(1).execute()
            latency_ms = round((time.time() - start_time) * 1000, 2)
            db_health = {
                "status": "connected",
                "latency_ms": latency_ms
            }
        except Exception as err:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            db_health = {
                "status": "disconnected",
                "latency_ms": latency_ms,
                "error": str(err)
            }
            is_healthy = False
    else:
        db_health = {"status": "not_configured"}

    status_str = "healthy" if is_healthy else "degraded"

    return {
        "status": status_str,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "environment": os.getenv("FLASK_ENV", "production"),
        "services": {
            "database": db_health,
            "sentry": {
                "status": "active" if _sentry_initialized else "disabled"
            }
        }
    }, (200 if is_healthy else 503)
