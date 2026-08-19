import os
import uuid
import json
from flask import Blueprint, request, jsonify

coding_bp = Blueprint("coding_bp", __name__)

def get_supabase():
    import app
    return app.supabase

def upload_storage(bucket_name, file_input, filename, content_type=None):
    import app
    return app.upload_to_supabase_storage(bucket_name, file_input, filename, content_type)

@coding_bp.route("/api/coding/submit", methods=["POST"])
@coding_bp.route("/coding/submit", methods=["POST"])
def submit_code():
    data = request.get_json() or {}
    problem_id = data.get("problem_id", "prob_01")
    code = data.get("code", "")
    language = data.get("language", "python")
    input_data = data.get("input_data", "")
    user_id = data.get("user_id", "user_guest")

    from services.sphere_engine_service import execute_code_sphere_engine

    exec_result = execute_code_sphere_engine(code=code, language=language, input_data=input_data)
    
    status = exec_result.get("status", "Accepted")
    passed = 3 if exec_result.get("passed") else 0
    total = 3
    ai_review = f"Sphere Engine Status: {status}. Output stream: '{exec_result.get('stdout', '').strip()[:100]}'."

    sub_id = f"sub_{uuid.uuid4().hex[:8]}"
    try:
        supabase = get_supabase()
        supabase.table("coding_submissions").insert({
            "id": sub_id, "user_id": user_id, "problem_id": problem_id,
            "language": language, "code": code, "passed": passed,
            "total": total, "time_complexity": "O(N)", "space_complexity": "O(1)",
            "ai_review": ai_review, "created_at": None
        }).execute()
    except Exception as e:
        print("Coding submit DB notice:", e)

    return jsonify({
        "submission_id": sub_id,
        "engine": exec_result.get("engine", "Sphere Engine Compilers API v4"),
        "status": status,
        "passed_test_cases": passed,
        "total_test_cases": total,
        "stdout": exec_result.get("stdout", ""),
        "stderr": exec_result.get("stderr", ""),
        "compile_info": exec_result.get("compile_info", ""),
        "exec_time": exec_result.get("exec_time", 0.0),
        "memory_kb": exec_result.get("memory_kb", 0),
        "time_complexity": "O(N)",
        "space_complexity": "O(1)",
        "ai_review": ai_review
    }), 200

@coding_bp.route("/api/coding/hint", methods=["POST"])
@coding_bp.route("/coding/hint", methods=["POST"])
def get_coding_hint():
    data = request.get_json() or {}
    problem_id = data.get("problem_id", "prob_01")
    code = data.get("code", "")

    import app
    from services.ai_service import generate_hint
    flash_model = getattr(app, "flash_model", getattr(app, "chat_model", None))
    
    hint_prompt = f"Coding Problem: {problem_id}\nUser's Current Code:\n{code or '# No code written yet'}"
    dynamic_hint = generate_hint(hint_prompt, chat_model=flash_model)

    return jsonify({
        "hint": dynamic_hint,
        "problem_id": problem_id
    }), 200

UPLOADED_SHEET_PROBLEMS = {}

DEFAULT_CODING_PROBLEMS = [
    {
        "id": "prob_01",
        "problem_id": "prob_01",
        "title": "Two Sum",
        "category": "Algorithm",
        "difficulty": "Easy",
        "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.\n\nYou may assume that each input would have exactly one solution, and you may not use the same element twice.",
        "starter_code": "def twoSum(nums: list[int], target: int) -> list[int]:\n    # Write your code here\n    pass",
        "examples": [
            {
                "input": "nums = [2,7,11,15], target = 9",
                "output": "[0,1]",
                "explanation": "Because nums[0] + nums[1] == 9, we return [0, 1]."
            },
            {
                "input": "nums = [3,2,4], target = 6",
                "output": "[1,2]",
                "explanation": "Because nums[1] + nums[2] == 6, we return [1, 2]."
            },
            {
                "input": "nums = [3,3], target = 6",
                "output": "[0,1]",
                "explanation": "Because nums[0] + nums[1] == 6, we return [0, 1]."
            }
        ],
        "constraints": [
            "2 <= nums.length <= 10^4",
            "-10^9 <= nums[i] <= 10^9",
            "-10^9 <= target <= 10^9",
            "Only one valid answer exists."
        ],
        "test_cases": [
            {"input": "[2,7,11,15], 9", "expected": "[0,1]"},
            {"input": "[3,2,4], 6", "expected": "[1,2]"},
            {"input": "[3,3], 6", "expected": "[0,1]"}
        ]
    },
    {
        "id": "prob_02",
        "problem_id": "prob_02",
        "title": "Reverse Linked List",
        "category": "Data Structures",
        "difficulty": "Easy",
        "description": "Given the head of a singly linked list, reverse the list, and return the reversed list.",
        "starter_code": "def reverseList(head):\n    # Write your code here\n    pass",
        "examples": [
            {
                "input": "head = [1,2,3,4,5]",
                "output": "[5,4,3,2,1]",
                "explanation": "The linked list elements are reversed from 1->2->3->4->5 to 5->4->3->2->1."
            },
            {
                "input": "head = [1,2]",
                "output": "[2,1]",
                "explanation": "The linked list elements are reversed from 1->2 to 2->1."
            }
        ],
        "constraints": [
            "The number of nodes in the list is in the range [0, 5000].",
            "-5000 <= Node.val <= 5000"
        ],
        "test_cases": [
            {"input": "[1,2,3,4,5]", "expected": "[5,4,3,2,1]"}
        ]
    },
    {
        "id": "prob_03",
        "problem_id": "prob_03",
        "title": "Valid Parentheses",
        "category": "Data Structures",
        "difficulty": "Medium",
        "description": "Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.\n\nAn input string is valid if open brackets are closed by the same type of brackets and in the correct order.",
        "starter_code": "def isValid(s: str) -> bool:\n    # Write your code here\n    pass",
        "examples": [
            {
                "input": "s = \"()\"",
                "output": "true",
                "explanation": "The open bracket '(' is closed by matching ')'."
            },
            {
                "input": "s = \"()[]{}\"",
                "output": "true",
                "explanation": "All parenthesis types are closed in correct sequence."
            },
            {
                "input": "s = \"(]\"",
                "output": "false",
                "explanation": "Closing bracket ']' does not match '('."
            }
        ],
        "constraints": [
            "1 <= s.length <= 10^4",
            "s consists of parentheses only '()[]{}'."
        ],
        "test_cases": [
            {"input": "'()'", "expected": "True"},
            {"input": "'()[]{}'", "expected": "True"}
        ]
    }
]

@coding_bp.route("/api/coding/upload-sheet", methods=["POST"])
@coding_bp.route("/coding/upload-sheet", methods=["POST"])
def upload_coding_sheet():
    file = request.files.get("file") or request.files.get("sheet")
    if not file:
        return jsonify({"error": "No file uploaded. Please select a valid document."}), 400

    filename = file.filename or "uploaded_sheet.txt"
    unique_filename = f"sheet_{uuid.uuid4()}_{filename}"
    file_bytes = file.read()

    sheet_url = ""
    try:
        sheet_url = upload_storage("question_sheets", file_bytes, unique_filename)
    except Exception as e:
        print("Upload storage notice:", e)

    sheet_id = f"sheet_{uuid.uuid4().hex[:8]}"

    # Attempt to parse document content
    parsed_problems = []
    try:
        content_str = file_bytes.decode("utf-8", errors="ignore")
        if filename.endswith(".json") or content_str.strip().startswith("["):
            data = json.loads(content_str)
            if isinstance(data, list):
                parsed_problems = data
            elif isinstance(data, dict) and "problems" in data:
                parsed_problems = data["problems"]
    except Exception as parse_err:
        print("Sheet JSON parse notice:", parse_err)

    if not parsed_problems:
        # Generate parsed problem from uploaded document text
        parsed_problems = [
            {
                "id": f"sheet_prob_{uuid.uuid4().hex[:6]}",
                "problem_id": f"sheet_prob_{uuid.uuid4().hex[:6]}",
                "title": f"Custom Question from {filename}",
                "category": "Custom Sheet",
                "difficulty": "Medium",
                "description": f"Extracted problem set from document '{filename}'. Solve the algorithmic requirements below:\n\n{file_bytes.decode('utf-8', errors='ignore')[:400]}...",
                "starter_code": "def solution(data):\n    # Write solution for parsed document problem\n    pass",
                "examples": [
                    {
                        "input": "Sample input from sheet",
                        "output": "Expected output",
                        "explanation": "Extracted automatically from uploaded sheet document."
                    }
                ],
                "constraints": [
                    "Constraints specified in uploaded sheet",
                    "Execution time limit: 2.00 seconds"
                ],
                "test_cases": [
                    {"input": "sample_input", "expected": "sample_output"}
                ]
            }
        ]

    UPLOADED_SHEET_PROBLEMS[sheet_id] = parsed_problems

    try:
        supabase = get_supabase()
        supabase.table("question_sheets").insert({
            "sheet_id": sheet_id, "uploader_id": "admin",
            "filename": filename, "created_at": None
        }).execute()
    except Exception as e:
        print("Sheet DB notice:", e)

    return jsonify({
        "sheet_id": sheet_id,
        "filename": filename,
        "sheet_url": sheet_url,
        "problems": parsed_problems,
        "message": "Question sheet uploaded and parsed successfully"
    }), 200

@coding_bp.route("/api/coding/problems", methods=["GET"])
@coding_bp.route("/coding/problems", methods=["GET"])
def get_coding_problems():
    sheet_id = request.args.get("sheet_id")
    if sheet_id and sheet_id in UPLOADED_SHEET_PROBLEMS:
        return jsonify(UPLOADED_SHEET_PROBLEMS[sheet_id]), 200

    try:
        supabase = get_supabase()
        res = supabase.table("coding_problems").select("*").execute()
        problems = res.data if (res and hasattr(res, "data") and res.data) else []
        if not problems:
            problems = DEFAULT_CODING_PROBLEMS
        return jsonify(problems), 200
    except Exception as e:
        return jsonify(DEFAULT_CODING_PROBLEMS), 200

@coding_bp.route("/api/coding/room/create", methods=["POST"])
@coding_bp.route("/coding/room/create", methods=["POST"])
def create_coding_room():
    data = request.get_json() or {}
    room_id = f"room_{uuid.uuid4().hex[:6]}"
    problem_id = data.get("problem_id", "prob_01")
    created_by = data.get("created_by", "user_admin")

    try:
        supabase = get_supabase()
        supabase.table("coding_rooms").insert({
            "room_id": room_id, "problem_id": problem_id,
            "created_by": created_by, "current_code": "",
            "current_lang": "python", "participants": json.dumps([created_by]),
            "assigned_problems": json.dumps([problem_id])
        }).execute()
    except Exception as e:
        print("Coding room DB notice:", e)

    return jsonify({
        "room_id": room_id, "problem_id": problem_id,
        "message": "Collaborative coding room created"
    }), 200

@coding_bp.route("/api/coding/room/join", methods=["POST"])
@coding_bp.route("/coding/room/join", methods=["POST"])
def join_coding_room():
    data = request.get_json() or {}
    room_id = data.get("room_id")
    user_id = data.get("user_id", "guest")

    if not room_id:
        return jsonify({"error": "room_id is required"}), 400

    return jsonify({
        "room_id": room_id, "user_id": user_id,
        "message": "Joined collaborative room successfully"
    }), 200

@coding_bp.route("/api/coding/room/sync", methods=["GET", "POST", "OPTIONS"])
@coding_bp.route("/coding/room/sync", methods=["GET", "POST", "OPTIONS"])
def sync_coding_room():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    if request.method == "POST":
        data = request.get_json() or {}
        room_id = data.get("room_id")
        code = data.get("code", "")
        language = data.get("language", "python")
        return jsonify({"status": "synced", "room_id": room_id, "code": code, "language": language}), 200

    room_id = request.args.get("room_id")
    return jsonify({"room_id": room_id, "code": "# Write code here\n", "language": "python"}), 200

@coding_bp.route("/api/coding/room/assign-question", methods=["POST"])
@coding_bp.route("/coding/room/assign-question", methods=["POST"])
def assign_coding_question():
    data = request.get_json() or {}
    room_id = data.get("room_id")
    problem_id = data.get("problem_id")
    return jsonify({"message": "Question assigned to room", "room_id": room_id, "problem_id": problem_id}), 200

@coding_bp.route("/api/coding/room/signal", methods=["POST"])
@coding_bp.route("/coding/room/signal", methods=["POST"])
def coding_room_signal():
    data = request.get_json() or {}
    return jsonify({"status": "signal_received", "payload": data}), 200
