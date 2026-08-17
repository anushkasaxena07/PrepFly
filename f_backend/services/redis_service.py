import os
import json
import logging
import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL") or os.getenv("UPSTASH_REDIS_URL") or "rediss://default:gQAAAAAAArgIAAIgcDI0NTNlNzY2YjhjODM0NDFiYmU3NzRjMmE2NDZmZTk4Yg@literate-moccasin-178184.upstash.io:6379"

_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        # Connect to Upstash Redis with SSL/TLS support enabled
        _redis_client = redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
        # Test connection ping
        _redis_client.ping()
        logging.info(f"[REDIS UPSTASH] Connected to Upstash Redis successfully: {REDIS_URL[:30]}...")
        return _redis_client
    except Exception as e:
        logging.warning(f"[REDIS NOTICE] Upstash Redis connection error: {e}. Operating with in-memory fallback.")
        return None

# Simple in-memory fallback store if Redis connection is temporarily offline
_memory_cache = {}

def cache_set(key: str, value: any, ttl_seconds: int = 3600) -> bool:
    r = get_redis_client()
    val_str = json.dumps(value) if not isinstance(value, str) else value
    if r:
        try:
            r.setex(key, ttl_seconds, val_str)
            return True
        except Exception as e:
            logging.warning(f"[REDIS CACHE SET NOTICE] Key '{key}': {e}")
    _memory_cache[key] = val_str
    return True

def cache_get(key: str):
    r = get_redis_client()
    if r:
        try:
            val = r.get(key)
            if val is not None:
                try: return json.loads(val)
                except Exception: return val
        except Exception as e:
            logging.warning(f"[REDIS CACHE GET NOTICE] Key '{key}': {e}")
    val = _memory_cache.get(key)
    if val is not None:
        try: return json.loads(val)
        except Exception: return val
    return None

def cache_delete(key: str) -> bool:
    r = get_redis_client()
    if r:
        try: r.delete(key)
        except Exception: pass
    _memory_cache.pop(key, None)
    return True

def rate_limit_check(key_identifier: str, limit: int = 10, window_seconds: int = 60) -> bool:
    """Atomic rate limiter using Redis INCR & EXPIRE."""
    r = get_redis_client()
    redis_key = f"rate_limit:{key_identifier}"
    if r:
        try:
            current = r.incr(redis_key)
            if current == 1:
                r.expire(redis_key, window_seconds)
            return current <= limit
        except Exception as e:
            logging.warning(f"[REDIS RATE LIMIT NOTICE] {e}")
    return True
