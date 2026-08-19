import os

# Port binding from Railway container PORT environment variable
port = os.getenv("PORT", "8080").strip()
if not port.isdigit():
    port = "8080"

bind = f"0.0.0.0:{port}"

# Worker & Thread Concurrency
workers = int(os.getenv("WEB_CONCURRENCY", 2))
worker_class = os.getenv("WORKER_CLASS", "gthread")
threads = int(os.getenv("PYTHON_GETHREADS", 4))

# Memory Protection & Worker Recycling
max_requests = int(os.getenv("MAX_REQUESTS", 1000))
max_requests_jitter = int(os.getenv("MAX_REQUESTS_JITTER", 50))

# Timeouts & Keepalive
timeout = int(os.getenv("GUNICORN_TIMEOUT", 120))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", 5))

# Logging
loglevel = os.getenv("LOG_LEVEL", "info").lower()
accesslog = "-"
errorlog = "-"
