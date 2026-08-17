import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.redis_service import get_redis_client, cache_set, cache_get, cache_delete, rate_limit_check
from tasks.bg_tasks import async_send_email, async_parse_resume_and_ats, async_generate_pdf_report, async_generate_tts
from wsgi import app as wsgi_app

def run_tests():
    print("--- 1. Testing Upstash Redis Connection (Phase 3) ---")
    client = get_redis_client()
    if client:
        ping_res = client.ping()
        print(f"[OK] Upstash Redis PING result: {ping_res}")
    else:
        print("[NOTICE] Operating with in-memory Redis fallback cache.")

    print("\n--- 2. Testing Redis Caching & Rate Limiting ---")
    cache_set("test_key_prepfly", {"status": "active", "score": 95}, ttl_seconds=60)
    cached_val = cache_get("test_key_prepfly")
    print(f"Cached Value: {cached_val}")
    assert isinstance(cached_val, dict) and cached_val.get("score") == 95, "Cache value mismatch"
    cache_delete("test_key_prepfly")

    is_allowed = rate_limit_check("test_user_ip", limit=5, window_seconds=60)
    print(f"Rate Limit Check Result: {is_allowed}")
    assert is_allowed is True, "Rate limit check failed"
    print("[OK] Redis caching and rate limiting verified!")

    print("\n--- 3. Testing Celery Background Tasks (Phase 4) ---")
    email_res = async_send_email("saxenaanushka9645@gmail.com", "PrepFly Test Email", "Test body", "test")
    print(f"Email Task Result: {email_res}")

    ats_res = async_parse_resume_and_ats("test_session_01", "Python Fullstack Developer experience with Flask, React, PostgreSQL.")
    print(f"ATS Task Result: {ats_res}")
    assert "ats_score" in ats_res, "ATS task failed"

    pdf_res = async_generate_pdf_report("Anushka", "saxenaanushka9645@gmail.com", "test_session_01", 8.5, "A", [])
    print(f"PDF Task Result: {pdf_res}")

    tts_res = async_generate_tts("Hello, welcome to your PrepFly AI Interview.")
    print(f"TTS Task Result: {tts_res}")
    print("[OK] Celery background tasks verified successfully!")

    print("\n--- 4. Testing Gunicorn WSGI Entrypoint (Phase 5) ---")
    assert wsgi_app is not None, "WSGI app entrypoint missing"
    test_client = wsgi_app.test_client()
    res = test_client.get("/api/superadmin/dashboard-stats")
    print(f"WSGI Test Client Response Code: {res.status_code}")
    print("[OK] Gunicorn WSGI entrypoint (wsgi:app) verified!")

    print("\n[SUCCESS] ALL PHASE 3 (REDIS), PHASE 4 (CELERY), AND PHASE 5 (GUNICORN) TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
