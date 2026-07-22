import sqlite3
import json
import os
import uuid
from datetime import datetime, timedelta
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_db.sqlite")

class SQLiteSupabaseMock:
    def __init__(self, db_path="local_db.sqlite"):
        # Make path absolute to the directory where this script is located
        dir_path = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(dir_path, db_path)
        self.storage = MockStorage()
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        conn.commit()
        
        # 1. users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                name TEXT,
                password TEXT,
                role TEXT,
                avatar TEXT,
                google_id TEXT,
                phone TEXT,
                created_at TEXT
            )
        """)
        
        # 2. pending_users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_users (
                email TEXT PRIMARY KEY,
                name TEXT,
                password TEXT,
                created_at TEXT
            )
        """)
        
        # 3. otps
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                otp TEXT,
                expires_at TEXT,
                is_used INTEGER DEFAULT 0,
                purpose TEXT
            )
        """)
        
        # 4. otp_requests
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otp_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                created_at TEXT
            )
        """)
        
        # 5. auth_logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                auth_method TEXT,
                success INTEGER,
                ip_address TEXT,
                timestamp TEXT
            )
        """)
        
        # 6. sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                resume_text TEXT,
                storage_path TEXT,
                question_index INTEGER,
                questions TEXT,
                responses TEXT,
                feedbacks TEXT,
                scores TEXT,
                active INTEGER DEFAULT 1,
                final_score REAL,
                final_grade TEXT,
                final_report TEXT,
                recording_path TEXT,
                category TEXT,
                difficulty TEXT,
                stage TEXT,
                ats_score INTEGER,
                structured_resume TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        session_cols = [
            ("category", "TEXT"),
            ("difficulty", "TEXT"),
            ("stage", "TEXT"),
            ("ats_score", "INTEGER"),
            ("structured_resume", "TEXT")
        ]
        for col_name, col_type in session_cols:
            try:
                cursor.execute(f"ALTER TABLE sessions ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass
        
        # 7. password_reset_tokens
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                token TEXT,
                expires_at TEXT,
                is_used INTEGER DEFAULT 0
            )
        """)
        
        # 8. coding_submissions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coding_submissions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                problem_id TEXT,
                language TEXT,
                code TEXT,
                passed INTEGER,
                total INTEGER,
                time_complexity TEXT,
                space_complexity TEXT,
                ai_review TEXT,
                created_at TEXT
            )
        """)

        # 9. speech_analyses
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS speech_analyses (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                transcript TEXT,
                confidence_pct REAL,
                wpm INTEGER,
                filler_count INTEGER,
                overall_score REAL,
                feedback TEXT,
                tone TEXT,
                created_at TEXT
            )
        """)

        # 10. resume_scores
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resume_scores (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                resume_text TEXT,
                job_description TEXT,
                score REAL,
                details TEXT,
                created_at TEXT
            )
        """)

        # 11. coding_problems
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coding_problems (
                problem_id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                constraints TEXT,
                examples TEXT,
                difficulty TEXT,
                category TEXT,
                starter_code TEXT,
                test_cases TEXT,
                sheet_id TEXT,
                created_at TEXT
            )
        """)

        # 12. coding_rooms
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coding_rooms (
                room_id TEXT PRIMARY KEY,
                problem_id TEXT,
                created_by TEXT,
                current_code TEXT,
                current_lang TEXT,
                participants TEXT,
                assigned_problems TEXT,
                created_at TEXT
            )
        """)

        # 13. webrtc_rooms
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webrtc_rooms (
                room_code TEXT PRIMARY KEY,
                session_name TEXT,
                category TEXT,
                created_by TEXT,
                devices TEXT,
                participants TEXT,
                status TEXT,
                created_at TEXT
            )
        """)

        # 14. question_sheets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_sheets (
                sheet_id TEXT PRIMARY KEY,
                uploader_id TEXT,
                filename TEXT,
                created_at TEXT
            )
        """)

        # 15. subscription
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscription (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                plan TEXT,
                price REAL,
                status TEXT,
                payment_id TEXT,
                payment_method TEXT,
                start_date TEXT,
                expiry_date TEXT,
                auto_renew INTEGER,
                created_at TEXT
            )
        """)

        # 16. payment
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment (
                id TEXT PRIMARY KEY,
                organization_id TEXT,
                razorpay_order_id TEXT,
                razorpay_payment_id TEXT,
                razorpay_signature TEXT,
                amount REAL,
                currency TEXT,
                invoice_number TEXT,
                status TEXT,
                payment_method TEXT,
                created_at TEXT
            )
        """)

        pay_cols = [
            ("organization_id", "TEXT"),
            ("razorpay_order_id", "TEXT"),
            ("razorpay_payment_id", "TEXT"),
            ("razorpay_signature", "TEXT"),
            ("amount", "REAL"),
            ("currency", "TEXT"),
            ("invoice_number", "TEXT"),
            ("status", "TEXT"),
            ("payment_method", "TEXT"),
            ("created_at", "TEXT")
        ]
        for col_name, col_type in pay_cols:
            try:
                cursor.execute(f"ALTER TABLE payment ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

        # 16b. invoice
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice (
                id TEXT PRIMARY KEY,
                payment_id TEXT,
                organization_id TEXT,
                invoice_number TEXT,
                amount REAL,
                gst REAL,
                created_at TEXT
            )
        """)

        inv_cols = [
            ("payment_id", "TEXT"),
            ("organization_id", "TEXT"),
            ("invoice_number", "TEXT"),
            ("amount", "REAL"),
            ("gst", "REAL"),
            ("created_at", "TEXT")
        ]
        for col_name, col_type in inv_cols:
            try:
                cursor.execute(f"ALTER TABLE invoice ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass
        conn.commit()

        # 17. admin
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id TEXT PRIMARY KEY,
                organization_id TEXT,
                name TEXT,
                email TEXT UNIQUE,
                password_hash TEXT,
                role TEXT,
                created_at TEXT
            )
        """)

        # 18. organization
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organization (
                id TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                logo TEXT,
                email TEXT,
                phone TEXT,
                website TEXT,
                address TEXT,
                subscription_status TEXT,
                trial_start TEXT,
                trial_end TEXT,
                subscription_start TEXT,
                subscription_expiry TEXT,
                current_plan TEXT,
                status TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        org_cols = [
            ("name", "TEXT"),
            ("type", "TEXT"),
            ("subscription_status", "TEXT"),
            ("subscription_plan", "TEXT"),
            ("trial_start", "TEXT"),
            ("trial_end", "TEXT"),
            ("subscription_start", "TEXT"),
            ("subscription_expiry", "TEXT"),
            ("current_plan", "TEXT"),
            ("status", "TEXT"),
            ("created_at", "TEXT"),
            ("updated_at", "TEXT")
        ]
        for col_name, col_type in org_cols:
            try:
                cursor.execute(f"ALTER TABLE organization ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass
        conn.commit()

        # 19. students (Multi-tenant)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id TEXT PRIMARY KEY,
                organization_id TEXT,
                name TEXT,
                roll_number TEXT,
                department TEXT,
                semester TEXT,
                year TEXT,
                gender TEXT,
                email TEXT,
                phone TEXT,
                resume_url TEXT,
                interview_score REAL,
                coding_score REAL,
                overall_score REAL,
                subscription TEXT,
                status TEXT,
                created_at TEXT
            )
        """)

        # 20. announcements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id TEXT PRIMARY KEY,
                organization_id TEXT,
                title TEXT,
                message TEXT,
                target_dept TEXT,
                target_sem TEXT,
                send_email INTEGER,
                send_notif INTEGER,
                created_at TEXT
            )
        """)

        # 21. question_bank
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_bank (
                id TEXT PRIMARY KEY,
                organization_id TEXT,
                title TEXT,
                category TEXT,
                difficulty TEXT,
                solution TEXT,
                created_at TEXT
            )
        """)

        # 22. admin_interviews
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_interviews (
                id TEXT PRIMARY KEY,
                organization_id TEXT,
                title TEXT,
                category TEXT,
                difficulty TEXT,
                questions_count INTEGER,
                student_id TEXT,
                scheduled_date TEXT,
                status TEXT,
                overall_score REAL,
                comm_score REAL,
                tech_score REAL,
                confidence_score REAL,
                created_at TEXT
            )
        """)

        # 23. admin_coding
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_coding (
                id TEXT PRIMARY KEY,
                organization_id TEXT,
                title TEXT,
                duration INTEGER,
                language TEXT,
                difficulty TEXT,
                visible_tests INTEGER,
                hidden_tests INTEGER,
                status TEXT,
                created_at TEXT
            )
        """)

        # 24. super_admin
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS super_admin (
                id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT UNIQUE,
                password_hash TEXT,
                role TEXT,
                avatar TEXT,
                created_at TEXT
            )
        """)

        # 25. platform_plans
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS platform_plans (
                id TEXT PRIMARY KEY,
                plan_name TEXT,
                target_type TEXT,
                price REAL,
                duration TEXT,
                storage_limit TEXT,
                student_limit TEXT,
                ai_interviews TEXT,
                coding_tests TEXT,
                reports TEXT,
                support TEXT,
                trial_days INTEGER,
                gst_pct REAL,
                created_at TEXT
            )
        """)

        # 26. ai_configuration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_configuration (
                id TEXT PRIMARY KEY,
                gemini_api_key TEXT,
                openai_api_key TEXT,
                temperature REAL,
                max_tokens INTEGER,
                interview_prompt TEXT,
                resume_prompt TEXT,
                coding_prompt TEXT,
                speech_model TEXT,
                status TEXT,
                updated_at TEXT
            )
        """)

        # 27. notifications
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                sender_type TEXT,
                sender_name TEXT,
                organization_id TEXT,
                target_group TEXT,
                title TEXT,
                message TEXT,
                target_dept TEXT,
                target_sem TEXT,
                created_at TEXT,
                read INTEGER DEFAULT 0
            )
        """)

        # 28. student_feedbacks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_feedbacks (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                student_id TEXT,
                student_name TEXT,
                organization_id TEXT,
                rating INTEGER,
                feedback_text TEXT,
                category TEXT,
                created_at TEXT
            )
        """)
        conn.commit()

        # 27. activity_logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id TEXT PRIMARY KEY,
                actor_id TEXT,
                actor_type TEXT,
                action TEXT,
                ip_address TEXT,
                details TEXT,
                created_at TEXT
            )
        """)

        # 28. support_tickets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id TEXT PRIMARY KEY,
                organization_id TEXT,
                user_name TEXT,
                email TEXT,
                subject TEXT,
                description TEXT,
                priority TEXT,
                status TEXT,
                assigned_to TEXT,
                created_at TEXT
            )
        """)

        # 28b. support_conversations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_conversations (
                id TEXT PRIMARY KEY,
                organization_id TEXT,
                admin_id TEXT,
                status TEXT,
                priority TEXT,
                category TEXT,
                subject TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # 28c. support_messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                sender_role TEXT,
                sender_id TEXT,
                message TEXT,
                attachment TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)

        # 28d. feedback
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                submitted_by TEXT,
                submitted_by_role TEXT,
                organization_id TEXT,
                subject TEXT,
                category TEXT,
                rating INTEGER DEFAULT 5,
                message TEXT,
                screenshot_url TEXT,
                status TEXT DEFAULT 'New',
                priority TEXT DEFAULT 'Medium',
                admin_notes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # 29. platform_settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS platform_settings (
                id TEXT PRIMARY KEY,
                platform_name TEXT,
                logo_url TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                timezone TEXT,
                maintenance_mode INTEGER,
                jwt_expiry_hours INTEGER,
                rate_limit_rpm INTEGER,
                updated_at TEXT
            )
        """)

        # Seed Default Super Admin Account
        cursor.execute("SELECT COUNT(*) FROM super_admin")
        if cursor.fetchone()[0] == 0:
            from werkzeug.security import generate_password_hash
            cursor.execute("""
                INSERT INTO super_admin (id, name, email, password_hash, role, avatar, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "super_admin_01",
                "Alex Vance (Platform Owner)",
                "superadmin@interviewai.io",
                generate_password_hash("superadmin123"),
                "SUPER_ADMIN",
                "https://lh3.googleusercontent.com/a/default_owner",
                datetime.utcnow().isoformat()
            ))

            # Seed AI Config
            cursor.execute("""
                INSERT INTO ai_configuration (id, gemini_api_key, openai_api_key, temperature, max_tokens, interview_prompt, resume_prompt, coding_prompt, speech_model, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "aiconfig_01",
                "AIzaSyDemoKeyGemini123456",
                "sk-demo-openai-key-7890",
                0.7,
                2048,
                "You are an expert technical interviewer evaluating candidates.",
                "Evaluate resume text against the job description for ATS match.",
                "Evaluate code execution time, space complexity, and test cases.",
                "whisper-1",
                "Active",
                datetime.utcnow().isoformat()
            ))

            # Seed Platform Plans
            plans = [
                ("plan_free", "Student Free Tier", "Student", 0, "Forever", "1 GB", "1 Student", "3 / Month", "5 / Month", "Basic", "Community", 0, 0),
                ("plan_student_pro", "Student Premium Pro", "Student", 299, "Monthly", "5 GB", "1 Student", "Unlimited", "Unlimited", "Detailed AI", "Priority SLA", 7, 18),
                ("plan_org_starter", "College Starter", "Organization", 999, "Annual", "50 GB", "250 Students", "1,000 / Year", "1,500 / Year", "Executive Digest", "Dedicated Account Manager", 14, 18),
                ("plan_org_enterprise", "Enterprise SaaS Unlimited", "Organization", 2499, "Annual", "500 GB", "1,000+ Students", "Unlimited", "Unlimited", "Custom AI Models", "24/7 Priority SLA", 14, 18)
            ]
            for p in plans:
                cursor.execute("""
                    INSERT INTO platform_plans (id, plan_name, target_type, price, duration, storage_limit, student_limit, ai_interviews, coding_tests, reports, support, trial_days, gst_pct, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[11], p[12], datetime.utcnow().isoformat()))

            # Seed Activity Logs
            cursor.execute("""
                INSERT INTO activity_logs (id, actor_id, actor_type, action, ip_address, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "log_01",
                "super_admin_01",
                "SUPER_ADMIN",
                "Platform Launch & Initial System Verification",
                "127.0.0.1",
                "Super Admin initialized platform configuration",
                datetime.utcnow().isoformat()
            ))

        # Seed Default Organization & Admin
        cursor.execute("SELECT COUNT(*) FROM admin")
        if cursor.fetchone()[0] == 0:
            from werkzeug.security import generate_password_hash
            org_id = "org_stanford_01"
            cursor.execute("""
                INSERT INTO organization (id, name, type, logo, email, phone, website, address, subscription_plan, subscription_expiry, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                org_id,
                "Stanford Tech Institute",
                "College",
                "https://lh3.googleusercontent.com/a/default_logo",
                "admin@stanford.edu",
                "+1 (650) 723-2300",
                "https://stanford.edu",
                "450 Jane Stanford Way, Stanford, CA",
                "ENTERPRISE",
                "2027-12-31",
                "Active",
                datetime.utcnow().isoformat()
            ))

            cursor.execute("""
                INSERT INTO admin (id, organization_id, name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "admin_01",
                org_id,
                "Prof. Marcus Vance",
                "admin@stanford.edu",
                generate_password_hash("admin123"),
                "Organization Admin",
                datetime.utcnow().isoformat()
            ))

            # Seed Sample Students under org_id
            sample_students = [
                ("std_101", org_id, "Aarav Sharma", "CS2023001", "Computer Science", "Sem 6", "3rd", "Male", "aarav@stanford.edu", "+91 9876543210", 8.8, 92.5, 9.0, "PREMIUM", "Active"),
                ("std_102", org_id, "Ananya Patel", "CS2023002", "Computer Science", "Sem 6", "3rd", "Female", "ananya@stanford.edu", "+91 9876543211", 9.2, 95.0, 9.4, "PREMIUM", "Active"),
                ("std_103", org_id, "Rohan Verma", "EC2023015", "Electronics", "Sem 4", "2nd", "Male", "rohan@stanford.edu", "+91 9876543212", 7.5, 81.0, 7.8, "FREE", "Active"),
                ("std_104", org_id, "Sneha Reddy", "IT2023008", "Information Tech", "Sem 8", "4th", "Female", "sneha@stanford.edu", "+91 9876543213", 8.9, 88.0, 8.8, "PREMIUM", "Active"),
                ("std_105", org_id, "Vikram Malhotra", "ME2023022", "Mechanical", "Sem 4", "2nd", "Male", "vikram@stanford.edu", "+91 9876543214", 6.8, 70.0, 6.9, "FREE", "Inactive")
            ]

            for s in sample_students:
                cursor.execute("""
                    INSERT INTO students (id, organization_id, name, roll_number, department, semester, year, gender, email, phone, interview_score, coding_score, overall_score, subscription, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7], s[8], s[9], s[10], s[11], s[12], s[13], s[14], datetime.utcnow().isoformat()))

        # Seed default coding problems
        cursor.execute("SELECT COUNT(*) FROM coding_problems")
        if cursor.fetchone()[0] == 0:
            default_problems = [
                {
                    "problem_id": "two-sum",
                    "title": "Two Sum",
                    "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume that each input would have exactly one solution, and you may not use the same element twice. You can return the answer in any order.",
                    "constraints": json.dumps([
                        "2 <= nums.length <= 10^4",
                        "-10^9 <= nums[i] <= 10^9",
                        "-10^9 <= target <= 10^9",
                        "Only one valid answer exists."
                    ]),
                    "examples": json.dumps([
                        {"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]", "explanation": "Because nums[0] + nums[1] == 9, we return [0, 1]."},
                        {"input": "nums = [3,2,4], target = 6", "output": "[1,2]"}
                    ]),
                    "difficulty": "Easy",
                    "category": "Arrays",
                    "starter_code": json.dumps({
                        "python": "def twoSum(nums, target):\n    # Write your code here\n    pass\n",
                        "javascript": "function twoSum(nums, target) {\n    // Write your code here\n    \n}\n",
                        "cpp": "#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    vector<int> twoSum(vector<int>& nums, int target) {\n        return {};\n    }\n};",
                        "java": "import java.util.*;\n\nclass Solution {\n    public int[] twoSum(int[] nums, int target) {\n        return new int[]{};\n    }\n}"
                    }),
                    "test_cases": json.dumps([
                        {"input": "[2, 7, 11, 15]\n9", "expected_output": "[0, 1]", "is_hidden": False},
                        {"input": "[3, 2, 4]\n6", "expected_output": "[1, 2]", "is_hidden": False},
                        {"input": "[3, 3]\n6", "expected_output": "[0, 1]", "is_hidden": True}
                    ]),
                    "sheet_id": None,
                    "created_at": datetime.utcnow().isoformat()
                },
                {
                    "problem_id": "reverse-string",
                    "title": "Reverse String",
                    "description": "Write a function that reverses a string. The input string is given as an array of characters s. You must do this by modifying the input array in-place with O(1) extra memory.",
                    "constraints": json.dumps([
                        "1 <= s.length <= 10^5",
                        "s[i] is a printable ascii character."
                    ]),
                    "examples": json.dumps([
                        {"input": "s = [\"h\",\"e\",\"l\",\"l\",\"o\"]", "output": "[\"o\",\"l\",\"l\",\"e\",\"h\"]"},
                        {"input": "s = [\"H\",\"a\",\"n\",\"n\",\"a\",\"h\"]", "output": "[\"h\",\"a\",\"n\",\"n\",\"a\",\"H\"]"}
                    ]),
                    "difficulty": "Easy",
                    "category": "Strings",
                    "starter_code": json.dumps({
                        "python": "def reverseString(s):\n    # Write your code here\n    # Modify s in-place, do not return anything\n    pass\n",
                        "javascript": "function reverseString(s) {\n    // Modify s in-place, do not return anything\n    \n}\n",
                        "cpp": "#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    void reverseString(vector<char>& s) {\n        \n    }\n};",
                        "java": "class Solution {\n    public void reverseString(char[] s) {\n        \n    }\n}"
                    }),
                    "test_cases": json.dumps([
                        {"input": "[\"h\",\"e\",\"l\",\"l\",\"o\"]", "expected_output": "[\"o\",\"l\",\"l\",\"e\",\"h\"]", "is_hidden": False},
                        {"input": "[\"H\",\"a\",\"n\",\"n\",\"a\",\"h\"]", "expected_output": "[\"h\",\"a\",\"n\",\"n\",\"a\",\"H\"]", "is_hidden": False},
                        {"input": "[\"a\"]", "expected_output": "[\"a\"]", "is_hidden": True}
                    ]),
                    "sheet_id": None,
                    "created_at": datetime.utcnow().isoformat()
                },
                {
                    "problem_id": "valid-parentheses",
                    "title": "Valid Parentheses",
                    "description": "Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid. An input string is valid if open brackets are closed by the same type of brackets and open brackets are closed in the correct order.",
                    "constraints": json.dumps([
                        "1 <= s.length <= 10^4",
                        "s consists of parentheses only '()[]{}'."
                    ]),
                    "examples": json.dumps([
                        {"input": "s = \"()\"", "output": "true"},
                        {"input": "s = \"()[]{}\"", "output": "true"},
                        {"input": "s = \"(]\"", "output": "false"}
                    ]),
                    "difficulty": "Easy",
                    "category": "Stack",
                    "starter_code": json.dumps({
                        "python": "def isValid(s):\n    # Write your code here\n    pass\n",
                        "javascript": "function isValid(s) {\n    // Write your code here\n    return false;\n}\n",
                        "cpp": "#include <string>\nusing namespace std;\n\nclass Solution {\npublic:\n    bool isValid(string s) {\n        return false;\n    }\n};",
                        "java": "class Solution {\n    public boolean isValid(String s) {\n        return false;\n    }\n}"
                    }),
                    "test_cases": json.dumps([
                        {"input": "\"()\"", "expected_output": "true", "is_hidden": False},
                        {"input": "\"(]\"", "expected_output": "false", "is_hidden": False},
                        {"input": "\"([)]\"", "expected_output": "false", "is_hidden": True},
                        {"input": "\"{[]}\"", "expected_output": "true", "is_hidden": True}
                    ]),
                    "sheet_id": None,
                    "created_at": datetime.utcnow().isoformat()
                }
            ]
            for p in default_problems:
                cursor.execute("""
                    INSERT INTO coding_problems 
                    (problem_id, title, description, constraints, examples, difficulty, category, starter_code, test_cases, sheet_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p["problem_id"], p["title"], p["description"], p["constraints"], p["examples"],
                    p["difficulty"], p["category"], p["starter_code"], p["test_cases"], p["sheet_id"], p["created_at"]
                ))
        
        conn.commit()
        conn.close()

    def table(self, name):
        return QueryBuilder(self, name)

class MockStorageBucket:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
    def upload(self, path, file, file_options=None):
        class DummyResult:
            def __init__(self, path):
                self.path = path
        return DummyResult(path)

class MockStorage:
    def from_(self, bucket_name):
        return MockStorageBucket(bucket_name)

class DummyResult:
    def __init__(self, data):
        self.data = data

class QueryBuilder:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.filters = []
        self.order_by = None
        self.limit_val = None
        self.operation = None
        self.data_to_write = None
        self.on_conflict = None
        self._maybe_single = False

    def select(self, columns="*"):
        self.operation = "select"
        self.columns = columns
        return self

    def insert(self, data):
        self.operation = "insert"
        self.data_to_write = data
        return self

    def update(self, data):
        self.operation = "update"
        self.data_to_write = data
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def upsert(self, data, on_conflict=None):
        self.operation = "upsert"
        self.data_to_write = data
        self.on_conflict = on_conflict
        return self

    def eq(self, column, value):
        self.filters.append(("eq", column, value))
        return self

    def neq(self, column, value):
        self.filters.append(("neq", column, value))
        return self

    def in_(self, column, values):
        self.filters.append(("in", column, values))
        return self

    def gte(self, column, value):
        self.filters.append(("gte", column, value))
        return self

    def order(self, column, desc=False):
        self.order_by = (column, desc)
        return self

    def limit(self, value):
        self.limit_val = value
        return self

    def maybe_single(self):
        self._maybe_single = True
        return self

    def execute(self):
        conn = self.client._get_conn()
        cursor = conn.cursor()
        
        # Get list of columns in the SQLite table dynamically
        cursor.execute(f"PRAGMA table_info({self.table_name})")
        columns_info = cursor.fetchall()
        table_cols = [info[1] for info in columns_info]
        integer_cols = [info[1] for info in columns_info if "INT" in info[2].upper()]
        
        filter_parts = []
        params = []
        for op, col, val in self.filters:
            if op == "eq":
                filter_parts.append(f"{col} = ?")
                params.append(val)
            elif op == "neq":
                filter_parts.append(f"{col} != ?")
                params.append(val)
            elif op == "gte":
                filter_parts.append(f"{col} >= ?")
                params.append(val)
            elif op == "in":
                placeholders = ",".join("?" for _ in val)
                filter_parts.append(f"{col} IN ({placeholders})")
                params.extend(val)
                
        where_clause = ""
        if filter_parts:
            where_clause = "WHERE " + " AND ".join(filter_parts)

        result_data = None

        def serialize_val(v):
            if isinstance(v, (list, dict)):
                return json.dumps(v)
            if isinstance(v, bool):
                return 1 if v else 0
            return v

        def deserialize_row(row):
            d = dict(row)
            for k, v in d.items():
                if isinstance(v, str):
                    v_strip = v.strip()
                    if (v_strip.startswith("[") and v_strip.endswith("]")) or (v_strip.startswith("{") and v_strip.endswith("}")):
                        try:
                            d[k] = json.loads(v)
                        except:
                            pass
                elif k in ("active", "success", "is_used") and v is not None:
                    d[k] = bool(v)
            return d

        if self.operation == "select":
            cols = self.columns
            if cols != "*":
                cols = ",".join(c.strip() for c in cols.split(","))
            
            sql = f"SELECT {cols} FROM {self.table_name} {where_clause}"
            if self.order_by:
                col, desc = self.order_by
                sql += f" ORDER BY {col} {'DESC' if desc else 'ASC'}"
            if self.limit_val:
                sql += f" LIMIT {self.limit_val}"
                
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            result_data = [deserialize_row(r) for r in rows]
            if self._maybe_single:
                result_data = result_data[0] if result_data else None

        elif self.operation == "insert":
            data_list = self.data_to_write if isinstance(self.data_to_write, list) else [self.data_to_write]
            inserted_rows = []
            for item in data_list:
                item = dict(item)
                if "id" in table_cols and "id" not in item:
                    if "id" not in integer_cols:
                        item["id"] = str(uuid.uuid4())
                if "created_at" in table_cols and "created_at" not in item:
                    item["created_at"] = datetime.utcnow().isoformat()
                
                keys = list(item.keys())
                vals = [serialize_val(item[k]) for k in keys]
                placeholders = ",".join("?" for _ in keys)
                sql = f"INSERT INTO {self.table_name} ({','.join(keys)}) VALUES ({placeholders})"
                cursor.execute(sql, vals)
                
                if "id" in item:
                    cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = ?", (item["id"],))
                elif "problem_id" in item:
                    cursor.execute(f"SELECT * FROM {self.table_name} WHERE problem_id = ?", (item["problem_id"],))
                elif "sheet_id" in item:
                    cursor.execute(f"SELECT * FROM {self.table_name} WHERE sheet_id = ?", (item["sheet_id"],))
                elif "room_id" in item:
                    cursor.execute(f"SELECT * FROM {self.table_name} WHERE room_id = ?", (item["room_id"],))
                elif "room_code" in item:
                    cursor.execute(f"SELECT * FROM {self.table_name} WHERE room_code = ?", (item["room_code"],))
                elif "email" in item:
                    cursor.execute(f"SELECT * FROM {self.table_name} WHERE email = ?", (item["email"],))
                elif "session_id" in item:
                    cursor.execute(f"SELECT * FROM {self.table_name} WHERE session_id = ?", (item["session_id"],))
                else:
                    cursor.execute(f"SELECT * FROM {self.table_name} WHERE rowid = ?", (cursor.lastrowid,))
                
                r = cursor.fetchone()
                if r:
                    inserted_rows.append(deserialize_row(r))
            
            conn.commit()
            result_data = inserted_rows

        elif self.operation == "update":
            item = dict(self.data_to_write)
            if "updated_at" in table_cols and "updated_at" not in item:
                item["updated_at"] = datetime.utcnow().isoformat()
            
            keys = list(item.keys())
            set_parts = [f"{k} = ?" for k in keys]
            vals = [serialize_val(item[k]) for k in keys]
            
            sql = f"UPDATE {self.table_name} SET {','.join(set_parts)} {where_clause}"
            cursor.execute(sql, vals + params)
            
            select_sql = f"SELECT * FROM {self.table_name} {where_clause}"
            cursor.execute(select_sql, params)
            rows = cursor.fetchall()
            updated_rows = [deserialize_row(r) for r in rows]
            
            conn.commit()
            result_data = updated_rows

        elif self.operation == "delete":
            select_sql = f"SELECT * FROM {self.table_name} {where_clause}"
            cursor.execute(select_sql, params)
            rows = cursor.fetchall()
            deleted_rows = [deserialize_row(r) for r in rows]
            
            sql = f"DELETE FROM {self.table_name} {where_clause}"
            cursor.execute(sql, params)
            conn.commit()
            result_data = deleted_rows

        elif self.operation == "upsert":
            data_list = self.data_to_write if isinstance(self.data_to_write, list) else [self.data_to_write]
            upserted_rows = []
            for item in data_list:
                item = dict(item)
                conflict_cols = []
                if self.on_conflict:
                    conflict_cols = [self.on_conflict] if isinstance(self.on_conflict, str) else list(self.on_conflict)
                else:
                    if self.table_name == "sessions":
                        conflict_cols = ["session_id"]
                    elif self.table_name == "users":
                        conflict_cols = ["id"]
                    elif self.table_name == "pending_users":
                        conflict_cols = ["email"]
                    elif self.table_name == "otps":
                        conflict_cols = ["id"]
                    elif self.table_name in ["support_conversations", "support_messages", "feedback"]:
                        conflict_cols = ["id"]
                
                exists = False
                exist_filters = []
                exist_params = []
                for col in conflict_cols:
                    if col in item:
                        exist_filters.append(f"{col} = ?")
                        exist_params.append(item[col])
                
                if exist_filters:
                    check_sql = f"SELECT * FROM {self.table_name} WHERE " + " AND ".join(exist_filters)
                    cursor.execute(check_sql, exist_params)
                    row = cursor.fetchone()
                    if row:
                        exists = True
                
                if exists:
                    if "updated_at" in table_cols and "updated_at" not in item:
                        item["updated_at"] = datetime.utcnow().isoformat()
                    keys = [k for k in item.keys() if k not in conflict_cols]
                    if keys:
                        set_parts = [f"{k} = ?" for k in keys]
                        vals = [serialize_val(item[k]) for k in keys]
                        update_sql = f"UPDATE {self.table_name} SET {','.join(set_parts)} WHERE " + " AND ".join(exist_filters)
                        cursor.execute(update_sql, vals + exist_params)
                else:
                    if "created_at" in table_cols and "created_at" not in item:
                        item["created_at"] = datetime.utcnow().isoformat()
                    keys = list(item.keys())
                    vals = [serialize_val(item[k]) for k in keys]
                    placeholders = ",".join("?" for _ in keys)
                    insert_sql = f"INSERT INTO {self.table_name} ({','.join(keys)}) VALUES ({placeholders})"
                    cursor.execute(insert_sql, vals)
                
                cursor.execute(f"SELECT * FROM {self.table_name} WHERE " + " AND ".join(exist_filters), exist_params)
                r = cursor.fetchone()
                if r:
                    upserted_rows.append(deserialize_row(r))
            
            conn.commit()
            result_data = upserted_rows

        conn.close()
        return DummyResult(result_data)

try:
    SQLiteSupabaseMock()
except Exception as e:
    print("Auto DB init notice:", e)