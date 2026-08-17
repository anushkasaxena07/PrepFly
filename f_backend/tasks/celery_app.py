import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL") or "rediss://default:gQAAAAAAArgIAAIgcDI0NTNlNzY2YjhjODM0NDFiYmU3NzRjMmE2NDZmZTk4Yg@literate-moccasin-178184.upstash.io:6379"

celery_app = Celery(
    "prepfly_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Dynamic Queue Concurrency & Worker Autoscaling Configuration
min_autoscale = int(os.getenv("CELERY_MIN_AUTOSCALE", "2"))
max_autoscale = int(os.getenv("CELERY_MAX_AUTOSCALE", "10"))

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_use_ssl={
        "ssl_cert_reqs": None
    },
    redis_backend_use_ssl={
        "ssl_cert_reqs": None
    },
    task_always_eager=False if os.getenv("CELERY_WORKER_ACTIVE") == "true" else True,
    
    # Celery Autoscaling & High Concurrency Settings
    worker_autoscale=(max_autoscale, min_autoscale),
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=500
)
