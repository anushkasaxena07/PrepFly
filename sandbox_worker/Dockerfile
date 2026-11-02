# PrepFly Isolated Sandbox Worker
# Hardened multi-language runtime with non-root execution and minimal capabilities

FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SANDBOX_PORT=5050 \
    SANDBOX_HOST=0.0.0.0

# Install compilers and runtimes: Node.js, GCC, G++, OpenJDK headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    nodejs \
    default-jdk-headless \
    default-jre-headless \
    ca-certificates \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged sandbox user and group (UID/GID 10001)
RUN groupadd -g 10001 sandboxgroup && \
    useradd -u 10001 -g sandboxgroup -s /bin/bash -m sandboxuser

WORKDIR /app

# Copy dependency definition and install
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker application source
COPY config.py security.py audit.py runner.py queue_manager.py server.py /app/

# Setup scratch directory with non-root ownership
RUN mkdir -p /app/scratch /tmp/sandbox && \
    chown -R sandboxuser:sandboxgroup /app /tmp/sandbox && \
    chmod 755 /app && \
    chmod 770 /tmp/sandbox

# Drop root privilege and switch to non-root user
USER sandboxuser:sandboxgroup

EXPOSE 5050

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:5050/health || exit 1

# Launch production WSGI server
CMD ["gunicorn", "--workers", "4", "--threads", "2", "--bind", "0.0.0.0:5050", "server:app"]
