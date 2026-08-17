import os
import sys
import multiprocessing

# Sanitize sys.argv to replace any literal '$PORT' passed by Railway CLI / Nixpacks
raw_port = os.getenv("PORT", "5000").strip()
if not raw_port.isdigit():
    raw_port = "5000"

new_argv = []
skip_next = False
for i, arg in enumerate(sys.argv):
    if skip_next:
        skip_next = False
        continue
    if "$PORT" in arg:
        arg = arg.replace("$PORT", raw_port)
    elif arg in ("-b", "--bind"):
        if i + 1 < len(sys.argv):
            next_arg = sys.argv[i + 1]
            if "$PORT" in next_arg:
                next_arg = next_arg.replace("$PORT", raw_port)
                new_argv.extend([arg, next_arg])
                skip_next = True
                continue
    new_argv.append(arg)

sys.argv = new_argv

bind = f"0.0.0.0:{raw_port}"
bind_env = os.getenv("BIND_ADDRESS")
if bind_env and "$" not in bind_env:
    bind = bind_env

# Worker Configuration for Container Environments (Default 2 workers, max 4 unless WEB_CONCURRENCY is explicitly set)
# Prevents Railway host machine core count (e.g. 32 physical cores = 65 workers) from causing OOM crashes
workers = int(os.getenv("WEB_CONCURRENCY", 2))

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
