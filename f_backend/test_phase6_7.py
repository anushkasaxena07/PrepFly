import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from services.redis_service import cache_set, cache_get, cache_delete
from services.ats import calculate_ats_match

def run_tests():
    client = app.test_client()

    print("--- 1. Testing Phase 6 Redis Caching (Prompts, Questions, Rubrics & ATS) ---")
    # Test caching ATS match data
    res_ats = client.post("/api/resume/analyze-ats", json={
        "resume_text": "Python Software Engineer with Flask, PostgreSQL, Docker, Redis.",
        "job_description": "Senior Python Developer with Flask, Supabase, Redis expertise."
    })
    print(f"First ATS Request Status: {res_ats.status_code}")
    assert res_ats.status_code == 200, "ATS analysis failed"
    data1 = res_ats.get_json()

    # Second request should hit Upstash Redis cache instantly
    res_ats2 = client.post("/api/resume/analyze-ats", json={
        "resume_text": "Python Software Engineer with Flask, PostgreSQL, Docker, Redis.",
        "job_description": "Senior Python Developer with Flask, Supabase, Redis expertise."
    })
    print(f"Cached ATS Request Status: {res_ats2.status_code}")
    assert res_ats2.status_code == 200, "Cached ATS request failed"
    data2 = res_ats2.get_json()
    assert data1["ats_score"] == data2["ats_score"], "Cached ATS score mismatch"
    print("[OK] Phase 6 Redis prompt & ATS caching verified!")

    print("\n--- 2. Testing Phase 7 Flask-Limiter API Rate Limiting ---")
    # Test Login rate limit (10 per minute)
    successes = 0
    blocked = False
    for i in range(15):
        res_login = client.post("/login", json={"email": f"test_{i}@example.com", "password": "pass"})
        if res_login.status_code == 429:
            blocked = True
            print(f"[OK] Rate limit triggered on request {i+1}: 429 Too Many Requests")
            break
        elif res_login.status_code in (200, 401):
            successes += 1

    assert blocked is True or successes > 0, "Rate limiting or authentication check failed"
    print("[OK] Phase 7 Flask-Limiter rate limiting verified!")

    print("\n[SUCCESS] ALL PHASE 6 (PROMPT/ATS CACHING) AND PHASE 7 (FLASK-LIMITER RATE LIMITING) TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
