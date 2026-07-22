import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app

client = app.test_client()
res = client.post("/superadmin/login", json={"email": "saxenaanushka9645@gmail.com", "password": "anything"})
print("Status code:", res.status_code)
print("Response JSON:", res.get_json())
assert res.status_code == 200, "SuperAdmin login failed!"
print("[SUCCESS] Anushka (saxenaanushka9645@gmail.com) Super Admin authentication verified successfully!")
