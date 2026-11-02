"""
Configuration for the PrepFly Isolated Sandbox Worker.
Defines security boundaries, resource limits, and execution policies.
"""

import os
from dataclasses import dataclass

@dataclass
class SandboxConfig:

    # Deployment Environment: "development", "test", "production"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", os.getenv("FLASK_ENV", "development")).lower()

    # Service Network Configuration
    HOST: str = os.getenv("SANDBOX_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("SANDBOX_PORT", "5050"))

    
    # Shared secret for inter-service authentication (constant-time verification)
    SECRET: str = os.getenv("ISOLATED_SANDBOX_SECRET", "prepfly-sandbox-dev-secret-32-chars-long-minimum")

    # Resource Limits per Execution
    CPU_TIME_LIMIT_SECONDS: float = float(os.getenv("SANDBOX_CPU_LIMIT", "2.0"))
    WALL_TIME_LIMIT_SECONDS: float = float(os.getenv("SANDBOX_WALL_LIMIT", "4.0"))
    COMPILATION_TIME_LIMIT_SECONDS: float = float(os.getenv("SANDBOX_COMPILE_LIMIT", "10.0"))
    MEMORY_LIMIT_BYTES: int = int(os.getenv("SANDBOX_MEM_LIMIT_BYTES", str(128 * 1024 * 1024)))  # 128 MB
    MAX_PROCESSES: int = int(os.getenv("SANDBOX_MAX_PROCS", "16"))  # Fork-bomb protection
    MAX_OUTPUT_BYTES: int = int(os.getenv("SANDBOX_MAX_OUTPUT_BYTES", str(64 * 1024)))  # 64 KB stdout/stderr
    MAX_CODE_SIZE_BYTES: int = int(os.getenv("SANDBOX_MAX_CODE_SIZE", str(64 * 1024)))  # 64 KB code

    # Concurrency and Queue Limits
    MAX_CONCURRENT_WORKERS: int = int(os.getenv("SANDBOX_CONCURRENT_WORKERS", "4"))
    MAX_QUEUE_CAPACITY: int = int(os.getenv("SANDBOX_QUEUE_CAPACITY", "50"))
    QUEUE_TIMEOUT_SECONDS: float = float(os.getenv("SANDBOX_QUEUE_TIMEOUT", "15.0"))

    # Rate Limiting & User Quotas
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("SANDBOX_RATE_LIMIT", "60"))
    USER_QUOTA_PER_MINUTE: int = int(os.getenv("SANDBOX_USER_QUOTA_PER_MINUTE", "15"))
    USER_QUOTA_PER_HOUR: int = int(os.getenv("SANDBOX_USER_QUOTA_PER_HOUR", "100"))
    USER_MAX_CONCURRENT_JOBS: int = int(os.getenv("SANDBOX_USER_MAX_CONCURRENT", "2"))
    GUEST_QUOTA_PER_MINUTE: int = int(os.getenv("SANDBOX_GUEST_QUOTA_PER_MINUTE", "5"))

    # Security & Audit Logging
    AUDIT_LOG_FILE: str = os.getenv("SANDBOX_AUDIT_LOG", "sandbox_audit.log")
    ENABLE_STATIC_AST_FILTER: bool = os.getenv("ENABLE_STATIC_AST_FILTER", "false").lower() == "true"
    
    # Isolation Backend Mode: "container", "microvm", "process", or "auto"
    ISOLATION_MODE: str = os.getenv("SANDBOX_ISOLATION_MODE", "auto")
    CONTAINER_IMAGE: str = os.getenv("SANDBOX_CONTAINER_IMAGE", "prepfly-sandbox-runner:latest")
    CONTAINER_RUNTIME: str = os.getenv("SANDBOX_CONTAINER_RUNTIME", "runc")  # or "runsc" for gVisor

    # Scratch and Isolation Directory Settings (supports SANDBOX_SCRATCH_DIR and SCRATCH_BASE_DIR)
    SCRATCH_BASE_DIR: str = os.getenv("SANDBOX_SCRATCH_DIR", os.getenv("SCRATCH_BASE_DIR", "")).strip()

config = SandboxConfig()

