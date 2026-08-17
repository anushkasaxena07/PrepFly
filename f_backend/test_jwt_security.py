import sys
import os
import jwt
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app
from middleware.auth import get_secret_key

def test_security():
    client = app.test_client()
    secret = get_secret_key()

    print("--- 1. Testing Unauthenticated Request (No Token) ---")
    res1 = client.get("/api/superadmin/dashboard-stats")
    print("Status:", res1.status_code, res1.get_json())
    assert res1.status_code == 401, "Expected 401 for missing token"
    print("[OK] Rejected unauthenticated request!")

    print("\n--- 2. Testing Forged Header Attack (X-User-Role: admin without JWT) ---")
    res2 = client.get("/api/superadmin/dashboard-stats", headers={
        "X-User-Role": "admin",
        "X-Super-Admin": "true"
    })
    print("Status:", res2.status_code, res2.get_json())
    assert res2.status_code == 401, "Expected 401 despite forged X-User-Role header"
    print("[OK] Successfully blocked forged header attack!")

    print("\n--- 3. Testing Tampered / Invalid JWT Token ---")
    res3 = client.get("/api/superadmin/dashboard-stats", headers={
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidpayload.invalidsignature"
    })
    print("Status:", res3.status_code, res3.get_json())
    assert res3.status_code == 401, "Expected 401 for tampered JWT"
    print("[OK] Successfully rejected tampered JWT!")

    print("\n--- 4. Testing Privilege Escalation (Candidate Token accessing SuperAdmin API) ---")
    cand_token = jwt.encode({
        "sub": "user_cand_01",
        "role": "candidate",
        "organization_id": "org_college_a",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }, secret, algorithm="HS256")

    res4 = client.get("/api/superadmin/dashboard-stats", headers={
        "Authorization": f"Bearer {cand_token}"
    })
    print("Status:", res4.status_code, res4.get_json())
    assert res4.status_code == 403, "Expected 403 Forbidden for candidate accessing SuperAdmin API"
    print("[OK] Successfully blocked candidate privilege escalation!")

    print("\n--- 5. Testing Verified Candidate Profile (/auth/me) ---")
    res5 = client.get("/auth/me", headers={
        "Authorization": f"Bearer {cand_token}"
    })
    print("Status:", res5.status_code, res5.get_json())
    assert res5.status_code == 200, "Expected 200 for valid candidate JWT on /auth/me"
    me_data = res5.get_json()
    assert me_data["user_id"] == "user_cand_01"
    assert me_data["role"] == "candidate"
    assert me_data["organization_id"] == "org_college_a"
    print("[OK] Candidate token claims verified successfully!")

    print("\n--- 6. Testing SuperAdmin JWT Authorized Request ---")
    sa_token = jwt.encode({
        "sub": "sa_anushka_01",
        "role": "SUPER_ADMIN",
        "organization_id": "org_prepfly_master",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }, secret, algorithm="HS256")

    res6 = client.get("/api/superadmin/dashboard-stats", headers={
        "Authorization": f"Bearer {sa_token}"
    })
    print("Status:", res6.status_code, res6.get_json())
    assert res6.status_code == 200, "Expected 200 for valid SuperAdmin JWT"
    print("[OK] SuperAdmin JWT authorization verified!")

    print("\n[SUCCESS] ALL JWT BEARER SECURITY AND AUTHORIZATION TESTS PASSED!")

if __name__ == "__main__":
    test_security()
