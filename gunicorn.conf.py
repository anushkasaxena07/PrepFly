import os

# Port binding: Render dynamically assigns PORT (defaulting to 10000 on Render)
port = os.getenv("PORT", "10000")
bind = f"0.0.0.0:{port}"

# Process & concurrency model: Render sets WEB_CONCURRENCY=1 by default on free tier
workers = int(os.getenv("WEB_CONCURRENCY", "1"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = 5

# Logging to stdout/stderr so Render live-tail logs capture arbiter & worker output
accesslog = "-"
errorlog = "-"
loglevel = "info"

