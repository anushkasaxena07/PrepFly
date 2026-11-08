import os

# Port binding: Bind to both 10000 and 5000 (and $PORT) so Render port detection always succeeds
env_port = os.getenv("PORT")
ports = ["10000", "5000"]
if env_port and env_port not in ports:
    ports.append(env_port)
bind = [f"0.0.0.0:{p}" for p in ports]

# Process & concurrency model: Render sets WEB_CONCURRENCY=1 by default on free tier
workers = int(os.getenv("WEB_CONCURRENCY", "1"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = 5

# Logging to stdout/stderr so Render live-tail logs capture arbiter & worker output
accesslog = "-"
errorlog = "-"
loglevel = "info"

