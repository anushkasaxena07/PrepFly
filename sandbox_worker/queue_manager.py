"""
Queue-based job dispatch and concurrency management for the sandbox worker.
Prevents server starvation by limiting concurrent executions and buffering tasks.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Callable, Dict, Optional

from config import config

class QueueManager:
    def __init__(
        self,
        max_workers: int = config.MAX_CONCURRENT_WORKERS,
        max_queue_size: int = config.MAX_QUEUE_CAPACITY
    ):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="sandbox-worker")
        self._active_jobs = 0
        self._lock = threading.Lock()
        self._total_jobs_processed = 0
        self._failed_jobs = 0
        self._timed_out_jobs = 0

    @property
    def active_jobs_count(self) -> int:
        with self._lock:
            return self._active_jobs

    @property
    def total_processed(self) -> int:
        with self._lock:
            return self._total_jobs_processed

    def get_metrics(self) -> Dict[str, Any]:
        """Returns snapshot of queue performance metrics."""
        with self._lock:
            return {
                "max_workers": self.max_workers,
                "max_queue_capacity": self.max_queue_size,
                "active_jobs": self._active_jobs,
                "total_processed": self._total_jobs_processed,
                "failed_jobs": self._failed_jobs,
                "timed_out_jobs": self._timed_out_jobs
            }

    def dispatch(
        self,
        task_fn: Callable[..., Dict[str, Any]],
        *args,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Submits a job to the bounded worker pool.
        Rejects immediately with an error if the queue is saturated.
        """
        with self._lock:
            if self._active_jobs >= (self.max_workers + self.max_queue_size):
                return {
                    "error": "Sandbox worker is saturated. Job queue capacity exceeded, please retry shortly.",
                    "status_code": 429
                }
            self._active_jobs += 1

        job_timeout = timeout or (config.WALL_TIME_LIMIT_SECONDS * 10 + config.QUEUE_TIMEOUT_SECONDS)
        future = self._executor.submit(task_fn, *args, **kwargs)

        try:
            result = future.result(timeout=job_timeout)
            with self._lock:
                self._total_jobs_processed += 1
            return result
        except TimeoutError:
            with self._lock:
                self._timed_out_jobs += 1
            return {
                "error": f"Job timed out in queue after {job_timeout} seconds",
                "status_code": 504
            }
        except Exception as e:
            with self._lock:
                self._failed_jobs += 1
            return {
                "error": f"Worker execution failure: {str(e)}",
                "status_code": 500
            }
        finally:
            with self._lock:
                self._active_jobs = max(0, self._active_jobs - 1)

queue_manager = QueueManager()

