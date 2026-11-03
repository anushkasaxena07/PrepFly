"""
Per-user and per-IP quota management for the PrepFly Isolated Sandbox Worker.
Enforces per-minute, per-hour, and concurrent execution bounds to prevent abuse,
resource exhaustion, and noisy neighbor interference.
"""

import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from config import config


class QuotaManager:
    def __init__(self):
        self._lock = threading.Lock()
        
        # Sliding window timestamps: key -> list of float epoch timestamps
        self._ip_requests: Dict[str, List[float]] = defaultdict(list)
        self._user_requests: Dict[str, List[float]] = defaultdict(list)
        
        # Active concurrent executions: key -> int
        self._user_active_jobs: Dict[str, int] = defaultdict(int)
        self._ip_active_jobs: Dict[str, int] = defaultdict(int)

    def _clean_old_records(self, timestamps: List[float], cutoff: float) -> List[float]:
        """Filters out timestamps older than the cutoff threshold."""
        return [ts for ts in timestamps if ts >= cutoff]

    def acquire(
        self,
        user_id: Optional[str],
        client_ip: str
    ) -> Tuple[bool, Optional[str], int]:
        """
        Attempts to acquire execution permission under per-user and per-IP quotas.
        Returns: (allowed: bool, reason: Optional[str], retry_after_seconds: int)
        """
        now = time.time()
        minute_cutoff = now - 60.0
        hour_cutoff = now - 3600.0

        with self._lock:
            # 1. Global IP Rate Limit Check
            clean_ip_ts = self._clean_old_records(self._ip_requests[client_ip], minute_cutoff)
            self._ip_requests[client_ip] = clean_ip_ts

            if len(clean_ip_ts) >= config.RATE_LIMIT_PER_MINUTE:
                oldest_in_window = clean_ip_ts[0]
                retry_after = max(1, int(60.0 - (now - oldest_in_window)))
                return False, f"IP rate limit exceeded ({config.RATE_LIMIT_PER_MINUTE}/min). Retry in {retry_after}s.", retry_after

            # 2. Authenticated User Quota Checks
            if user_id:
                # Concurrent execution limit
                if self._user_active_jobs[user_id] >= config.USER_MAX_CONCURRENT_JOBS:
                    return False, f"Concurrent execution limit reached ({config.USER_MAX_CONCURRENT_JOBS} max in flight). Please wait for active run to finish.", 2

                user_ts = self._clean_old_records(self._user_requests[user_id], hour_cutoff)
                self._user_requests[user_id] = user_ts

                # Per-minute quota
                recent_minute = [ts for ts in user_ts if ts >= minute_cutoff]
                if len(recent_minute) >= config.USER_QUOTA_PER_MINUTE:
                    retry_after = max(1, int(60.0 - (now - recent_minute[0])))
                    return False, f"User quota exceeded ({config.USER_QUOTA_PER_MINUTE} runs/minute). Retry in {retry_after}s.", retry_after

                # Per-hour quota
                if len(user_ts) >= config.USER_QUOTA_PER_HOUR:
                    retry_after = max(1, int(3600.0 - (now - user_ts[0])))
                    return False, f"User hourly quota exceeded ({config.USER_QUOTA_PER_HOUR} runs/hour). Retry in {retry_after}s.", retry_after

                # Record usage and acquire slot
                self._user_requests[user_id].append(now)
                self._user_active_jobs[user_id] += 1

            else:
                # 3. Unauthenticated / Guest IP Quota
                guest_recent = [ts for ts in clean_ip_ts if ts >= minute_cutoff]
                if len(guest_recent) >= config.GUEST_QUOTA_PER_MINUTE:
                    retry_after = max(1, int(60.0 - (now - guest_recent[0])))
                    return False, f"Guest quota exceeded ({config.GUEST_QUOTA_PER_MINUTE} runs/minute). Please log in for higher quotas.", retry_after

            # Record IP timestamp and acquire IP concurrency slot
            self._ip_requests[client_ip].append(now)
            self._ip_active_jobs[client_ip] += 1

            return True, None, 0

    def release(self, user_id: Optional[str], client_ip: str) -> None:
        """Releases the concurrent execution slot once execution finishes."""
        with self._lock:
            if user_id and user_id in self._user_active_jobs:
                self._user_active_jobs[user_id] = max(0, self._user_active_jobs[user_id] - 1)
                if self._user_active_jobs[user_id] == 0:
                    del self._user_active_jobs[user_id]

            if client_ip in self._ip_active_jobs:
                self._ip_active_jobs[client_ip] = max(0, self._ip_active_jobs[client_ip] - 1)
                if self._ip_active_jobs[client_ip] == 0:
                    del self._ip_active_jobs[client_ip]

    def get_stats(self) -> Dict[str, object]:
        """Provides operational snapshot of current quota tracking."""
        with self._lock:
            return {
                "active_users_in_flight": len(self._user_active_jobs),
                "total_tracked_users": len(self._user_requests),
                "total_tracked_ips": len(self._ip_requests),
                "active_ip_jobs": sum(self._ip_active_jobs.values())
            }


quota_manager = QuotaManager()
