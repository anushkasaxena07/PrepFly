import os
import multiprocessing

# Gunicorn Production Autoscaling Configuration

raw_port = os.getenv("PORT", "5000").strip()
if not raw_port.isdigit():
    raw_port = "5000"

bind_env = os.getenv("BIND_ADDRESS")
if bind_env and not bind_env.startswith("$"):
    bind = bind_env
else:
    bind = f"0.0.0.0:{raw_port}"

# Dynamic CPU-based worker autoscaling calculation (2 * cores + 1)
cpu_cores = multiprocessing.cpu_count()
default_workers = (cpu_cores * 2) + 1
workers = int(os.getenv("WEB_CONCURRENCY", default_workers))

# Async Threaded Worker Configuration for High Concurrency
worker_class = os.getenv("WORKER_CLASS", "gthread")
threads = int(os.getenv("PYTHON_GETHREADS", 4))

# Memory Protection & Worker Recycling to prevent memory leaks during traffic spikes
max_requests = int(os.getenv("MAX_REQUESTS", 1000))
max_requests_jitter = int(os.getenv("MAX_REQUESTS_JITTER", 50))

# Timeouts & Keepalive
timeout = int(os.getenv("GUNICORN_TIMEOUT", 120))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", 5))

# Logging
loglevel = os.getenv("LOG_LEVEL", "info").lower()
accesslog = "-"
errorlog = "-"
