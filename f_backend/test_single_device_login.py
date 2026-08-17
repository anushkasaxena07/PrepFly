import os
import sys
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from middleware.auth import set_active_session, ACTIVE_USER_SESSIONS

def test_single_device_login_flow():
    client = app.test_client()

    # 1. SuperAdmin Login Device A
    resp_sa_a = client.post("/superadmin/login", json={"email": "sa_test@prepfly.com"})
    assert resp_sa_a.status_code == 200
    data_sa_a = resp_sa_a.get_json()
    token_sa_a = data_sa_a["access_token"]
    session_sa_a = data_sa_a["session_id"]
    assert token_sa_a and session_sa_a

    # Verify Device A works
    resp_me_a = client.get("/superadmin/dashboard-stats", headers={"Authorization": f"Bearer {token_sa_a}"})
    assert resp_me_a.status_code == 200

    # 2. SuperAdmin Login Device B (overrides Device A)
    resp_sa_b = client.post("/superadmin/login", json={"email": "sa_test@prepfly.com"})
    assert resp_sa_b.status_code == 200
    data_sa_b = resp_sa_b.get_json()
    token_sa_b = data_sa_b["access_token"]
    session_sa_b = data_sa_b["session_id"]
    assert session_sa_a != session_sa_b

    # Verify Device B works
    resp_me_b = client.get("/superadmin/dashboard-stats", headers={"Authorization": f"Bearer {token_sa_b}"})
    assert resp_me_b.status_code == 200

    # Verify Device A is NOW INVALIDATED
    resp_me_a_superseded = client.get("/superadmin/dashboard-stats", headers={"Authorization": f"Bearer {token_sa_a}"})
    assert resp_me_a_superseded.status_code == 401
    err_data = resp_me_a_superseded.get_json()
    assert err_data.get("code") == "SESSION_SUPERSEEDED"
    print("SUCCESS: SINGLE DEVICE LOGIN ENFORCEMENT VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    test_single_device_login_flow()
