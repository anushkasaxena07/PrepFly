"""
Structured Audit Logging for PrepFly Sandbox Worker.
Records all execution events, security flags, timeouts, and resource usage.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

class AuditLogger:
    def __init__(self, log_file: Optional[str] = None):
        self.logger = logging.getLogger("prepfly.sandbox.audit")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        
        # Avoid duplicate handlers
        if not self.logger.handlers:
            formatter = logging.Formatter("%(message)s")
            
            # Console handler
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)
            
            # Rotating file handler if path provided
            if log_file:
                try:
                    from logging.handlers import RotatingFileHandler
                    file_handler = RotatingFileHandler(
                        log_file,
                        maxBytes=10 * 1024 * 1024,  # 10 MB
                        backupCount=5,
                        encoding="utf-8"
                    )
                    file_handler.setFormatter(formatter)
                    self.logger.addHandler(file_handler)
                except Exception as e:
                    print(f"[AUDIT] Warning: Could not setup file log handler: {e}", file=sys.stderr)

    def log_event(
        self,
        event_type: str,
        job_id: str,
        client_ip: str,
        language: str,
        problem_id: str,
        status: str,
        user_id: Optional[str] = None,
        isolation_mode: Optional[str] = None,
        execution_time_ms: float = 0.0,
        memory_kb: float = 0.0,
        security_flags: Optional[list] = None,
        error: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a structured security audit event."""
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "job_id": job_id,
            "client_ip": client_ip,
            "user_id": user_id or "anonymous",
            "isolation_mode": isolation_mode or "unknown",
            "language": language,
            "problem_id": problem_id,
            "status": status,
            "execution_time_ms": round(execution_time_ms, 2),
            "memory_kb": round(memory_kb, 2),
            "security_flags": security_flags or [],
            "error": error,
            "extra": extra or {}
        }
        self.logger.info(json.dumps(payload))

    def get_recent_logs(self, limit: int = 50) -> list:
        """Retrieves the most recent audit log entries."""
        log_file = os.getenv("SANDBOX_AUDIT_LOG", "sandbox_audit.log")
        if not os.path.exists(log_file):
            return []
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            records = []
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                    if len(records) >= limit:
                        break
                except Exception:
                    continue
            return records
        except Exception:
            return []

audit_logger = AuditLogger(os.getenv("SANDBOX_AUDIT_LOG", "sandbox_audit.log"))

