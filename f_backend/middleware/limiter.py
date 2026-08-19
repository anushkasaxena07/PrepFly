import os
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL") or "rediss://default:gQAAAAAAArgIAAIgcDI0NTNlNzY2YjhjODM0NDFiYmU3NzRjMmE2NDZmZTk4Yg@literate-moccasin-178184.upstash.io:6379"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL,
    storage_options={"ssl_cert_reqs": None},
    default_limits=["5000 per day", "1000 per hour", "200 per minute"],
    strategy="fixed-window"
)

@limiter.request_filter
def exempt_options_and_health_requests():
    return request.method == "OPTIONS" or request.path in ("/health", "/ready", "/system/health", "/system/ready")
