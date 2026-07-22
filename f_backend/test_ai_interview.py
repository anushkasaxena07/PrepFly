import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

def run_tests():
    client = app.test_client()
    print("--- 1. Testing Resume Upload & Structured Parsing ---")
    
    # Create sample dummy PDF text or DOCX
    dummy_resume = "B.Tech Computer Science student with skills in Python, React, Flask, Node.js, and SQL. Built E-Commerce Platform."
    
    # Test create session without resume first
    res = client.post("/create-session-no-resume", json={
        "role": "Full Stack Engineer",
        "tools": "React, Python, Node",
        "experience": "1 Year",
        "category": "DSA",
        "difficulty": "Medium"
    })
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.get_json()
    session_id = data["session_id"]
    print(f"[OK] Created session without resume: {session_id}")

    print("--- 2. Testing Start Recruiter Interview ---")
    res = client.post("/start-interview", json={"session_id": session_id})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    start_data = res.get_json()
    print(f"Question 1: {start_data['question']}")
    print(f"Stage: {start_data['stage']}")
    print("[OK] Start interview passed!")

    print("--- 3. Testing Next Question & Live Evaluation ---")
    res = client.post("/next", json={
        "session_id": session_id,
        "answer": "For this project, I used React for the frontend and Flask for the REST API. We implemented JWT authentication and deployed on Vercel."
    })
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    next_data = res.get_json()
    print(f"Feedback score: {next_data['feedback']['score']}/10")
    print(f"Next question: {next_data['next_question']}")
    print(f"Stage: {next_data['stage']}")
    print("[OK] Next question passed!")

    print("--- 4. Testing Hint Generation ---")
    res = client.post("/get-hint", json={"session_id": session_id})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    hint_data = res.get_json()
    print(f"Hint: {hint_data['hint']}")
    print("[OK] Hint generation passed!")

    print("--- 5. Testing End Interview ---")
    res = client.post("/end-interview", json={"session_id": session_id})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    end_data = res.get_json()
    print(f"Overall score: {end_data['overall_score']}, Grade: {end_data['grade']}")
    print("[OK] End interview passed!")

    print("\n[SUCCESS] ALL AI RECRUITER INTERVIEW SYSTEM TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
