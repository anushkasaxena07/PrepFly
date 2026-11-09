import sqlite3
import json
import os
import uuid
import re
from datetime import datetime, timedelta

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def _validate_ident(name: str) -> str:
    if not isinstance(name, str) or not IDENT_RE.match(name.strip()):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name.strip()

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_db.sqlite")

class SQLiteSupabaseMock:
    def __init__(self, db_path="local_db.sqlite"):
        if db_path in (":memory:", "file::memory:?cache=shared"):
            self.db_path = ":memory:"
            self._anchor_conn = sqlite3.connect("file:memdb_prepfly?mode=memory&cache=shared", uri=True, timeout=60, check_same_thread=False)
            self._anchor_conn.row_factory = sqlite3.Row
        else:
            dir_path = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(dir_path, db_path) if not os.path.isabs(db_path) else db_path
            self._anchor_conn = None
        self.storage = MockStorage()
        self._init_db()

    def _get_conn(self):
        if self.db_path == ":memory:":
            conn = sqlite3.connect("file:memdb_prepfly?mode=memory&cache=shared", uri=True, timeout=60, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        try:
            conn = sqlite3.connect(self.db_path, timeout=60, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 60000")
            return conn
        except Exception:
            if not self._anchor_conn:
                self._anchor_conn = sqlite3.connect("file:memdb_prepfly?mode=memory&cache=shared", uri=True, timeout=60, check_same_thread=False)
            conn = sqlite3.connect("file:memdb_prepfly?mode=memory&cache=shared", uri=True, timeout=60, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn

    def _init_db(self):
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            if self.db_path != ":memory:":
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("SELECT 1")
        except sqlite3.OperationalError:
            self.db_path = ":memory:"
            if not self._anchor_conn:
                self._anchor_conn = sqlite3.connect("file:memdb_prepfly?mode=memory&cache=shared", uri=True, timeout=60, check_same_thread=False)
                self._anchor_conn.row_factory = sqlite3.Row
            conn = self._get_conn()
            cursor = conn.cursor()
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
            ("structured_resume", "TEXT"),
            ("cached_hints", "TEXT"),
            ("interview_state", "TEXT DEFAULT 'INITIALIZING'"),
            ("personality", "TEXT DEFAULT 'professional'"),
            ("knowledge_map", "TEXT DEFAULT '{}'"),
            ("idempotency_key", "TEXT"),
            ("turn_count", "INTEGER DEFAULT 0"),
            ("role", "TEXT"),
            ("interview_mode", "TEXT"),
            ("total_questions", "INTEGER DEFAULT 10"),
            ("consent_given", "INTEGER DEFAULT 1"),
            ("consent_timestamp", "TEXT"),
            ("privacy_policy_version", "TEXT"),
            ("job_description", "TEXT"),
            ("organization_id", "TEXT")
        ]
        for col_name, col_type in session_cols:
            try:
                cursor.execute(f"ALTER TABLE sessions ADD COLUMN {_validate_ident(col_name)} {col_type}")
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
                current_output TEXT,
                last_editor TEXT,
                last_editor_name TEXT,
                participants TEXT,
                assigned_problems TEXT,
                created_at TEXT
            )
        """)
        for col in ["current_output", "last_editor", "last_editor_name"]:
            try:
                cursor.execute(f"ALTER TABLE coding_rooms ADD COLUMN {_validate_ident(col)} TEXT")
            except Exception:
                pass


        # 14. pending_users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_users (
                email TEXT PRIMARY KEY,
                name TEXT,
                password TEXT,
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
                cursor.execute(f"ALTER TABLE payment ADD COLUMN {_validate_ident(col_name)} {col_type}")
            except Exception:
                pass
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_order_success ON payment(razorpay_order_id) WHERE status = 'Success'")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_rzp_pay_success ON payment(razorpay_payment_id) WHERE status = 'Success'")

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
                cursor.execute(f"ALTER TABLE invoice ADD COLUMN {_validate_ident(col_name)} {col_type}")
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
                cursor.execute(f"ALTER TABLE organization ADD COLUMN {_validate_ident(col_name)} {col_type}")
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
                description TEXT,
                starter_code TEXT,
                test_cases TEXT,
                constraints TEXT,
                created_at TEXT
            )
        """)
        # Run migrations for existing DBs
        for col_name in ["description", "starter_code", "test_cases", "constraints"]:
            try:
                cursor.execute(f"ALTER TABLE question_bank ADD COLUMN {_validate_ident(col_name)} TEXT")
            except sqlite3.OperationalError:
                pass


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

        # 28c2. orders (Payment Orders)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                organization_id TEXT,
                plan_id TEXT,
                amount REAL,
                currency TEXT,
                status TEXT,
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

        # 30. candidate_profiles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidate_profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                target_company TEXT,
                target_role TEXT NOT NULL,
                experience_level TEXT NOT NULL,
                target_interview_date TEXT,
                preparation_duration_days INTEGER DEFAULT 30,
                daily_study_hours REAL DEFAULT 2.0,
                preferred_study_days TEXT,
                current_skills TEXT,
                preferred_language TEXT DEFAULT 'python',
                preparation_goals TEXT,
                strengths TEXT,
                growth_areas TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 31. skills
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                skill_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                parent_skill_id TEXT,
                difficulty TEXT NOT NULL,
                description TEXT,
                learning_objectives TEXT,
                assessment_criteria TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 32. skill_prerequisites
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_prerequisites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT NOT NULL,
                prerequisite_skill_id TEXT NOT NULL,
                is_mandatory INTEGER DEFAULT 1,
                UNIQUE(skill_id, prerequisite_skill_id)
            )
        """)

        # 33. role_skill_requirements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_skill_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                importance_weight REAL DEFAULT 1.0,
                minimum_proficiency REAL DEFAULT 60.0,
                UNIQUE(role_id, skill_id)
            )
        """)

        # 34. candidate_skill_profiles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidate_skill_profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                proficiency REAL DEFAULT 0.0,
                confidence REAL DEFAULT 0.0,
                evidence_count INTEGER DEFAULT 0,
                last_assessed TEXT,
                historical_proficiency TEXT,
                learning_trend TEXT DEFAULT 'stable',
                strong_concepts TEXT,
                growth_concepts TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, skill_id)
            )
        """)

        # 35. skill_evidence
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_evidence (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_id TEXT,
                score REAL NOT NULL,
                weight REAL DEFAULT 1.0,
                demonstrated_concepts TEXT,
                missed_concepts TEXT,
                misconceptions TEXT,
                evidence_notes TEXT,
                rubric_version TEXT DEFAULT 'v1',
                created_at TEXT NOT NULL
            )
        """)

        # 36. assessments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assessments (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                assessment_type TEXT NOT NULL,
                target_role TEXT,
                status TEXT DEFAULT 'pending',
                score REAL,
                total_questions INTEGER DEFAULT 0,
                completed_questions INTEGER DEFAULT 0,
                summary TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)

        # 37. assessment_questions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assessment_questions (
                id TEXT PRIMARY KEY,
                assessment_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                options TEXT,
                correct_answer TEXT,
                expected_concepts TEXT,
                rubric TEXT,
                order_index INTEGER DEFAULT 0
            )
        """)

        # 38. assessment_attempts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assessment_attempts (
                id TEXT PRIMARY KEY,
                assessment_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                candidate_answer TEXT,
                is_correct INTEGER,
                score REAL,
                evaluation_result TEXT,
                identified_concepts TEXT,
                missing_concepts TEXT,
                misconceptions TEXT,
                feedback TEXT,
                evaluated_at TEXT NOT NULL
            )
        """)

        # 39. roadmaps
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roadmaps (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                target_role TEXT NOT NULL,
                target_company TEXT,
                current_version INTEGER DEFAULT 1,
                total_days INTEGER DEFAULT 30,
                total_activities INTEGER DEFAULT 0,
                completed_activities INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 40. roadmap_versions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roadmap_versions (
                id TEXT PRIMARY KEY,
                roadmap_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                change_reason TEXT NOT NULL,
                trigger_event TEXT,
                activities_snapshot TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 41. roadmap_activities
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roadmap_activities (
                id TEXT PRIMARY KEY,
                roadmap_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                day_number INTEGER NOT NULL,
                order_in_day INTEGER DEFAULT 1,
                title TEXT NOT NULL,
                description TEXT,
                activity_type TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                estimated_minutes INTEGER DEFAULT 30,
                learning_objective TEXT,
                completion_criteria TEXT,
                priority REAL DEFAULT 1.0,
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                is_pinned INTEGER DEFAULT 0,
                recommendation_reason TEXT,
                resource_payload TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 42. activity_attempts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_attempts (
                id TEXT PRIMARY KEY,
                activity_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL,
                time_spent_minutes INTEGER DEFAULT 0,
                performance_score REAL,
                notes TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 43. revision_schedules
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS revision_schedules (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                interval_stage INTEGER DEFAULT 1,
                next_due_at TEXT,
                next_revision_date TEXT,
                due_date TEXT,
                last_reviewed_at TEXT,
                last_score REAL DEFAULT 0.0,
                retrieval_attempts INTEGER DEFAULT 0,
                easiness_factor REAL DEFAULT 2.5,
                status TEXT DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        for col_name, col_type in [
            ("next_due_at", "TEXT"),
            ("due_date", "TEXT"),
            ("last_score", "REAL DEFAULT 0.0"),
            ("retrieval_attempts", "INTEGER DEFAULT 0"),
            ("easiness_factor", "REAL DEFAULT 2.5"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE revision_schedules ADD COLUMN {_validate_ident(col_name)} {col_type}")
            except Exception:
                pass

        # 44. interview_turns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interview_turns (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT,
                stage TEXT,
                candidate_response TEXT,
                intent TEXT DEFAULT 'ANSWER',
                decision TEXT DEFAULT 'NEXT_QUESTION',
                score REAL DEFAULT 0.0,
                accuracy_score INTEGER DEFAULT 0,
                evaluation_json TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 45. interviewer_profiles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interviewer_profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                tone TEXT NOT NULL,
                formality TEXT NOT NULL,
                probing_intensity TEXT NOT NULL,
                encouragement_frequency TEXT NOT NULL,
                hint_policy TEXT NOT NULL,
                system_prompt_modifier TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # 46. candidate_resume_claims
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidate_resume_claims (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                claim_type TEXT NOT NULL,
                claim_text TEXT NOT NULL,
                provenance_section TEXT,
                confidence REAL DEFAULT 1.0,
                created_at TEXT NOT NULL
            )
        """)

        # 47. preparation_events
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preparation_events (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source_module TEXT NOT NULL,
                source_record_id TEXT,
                payload_json TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 48. job_profiles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                job_title TEXT NOT NULL,
                company TEXT,
                raw_text TEXT NOT NULL,
                role_tier TEXT DEFAULT 'mid',
                target_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 49. job_requirements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_requirements (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                normalized_skill_id TEXT NOT NULL,
                requirement_type TEXT NOT NULL,
                is_required INTEGER DEFAULT 1,
                importance_weight REAL DEFAULT 3.0,
                evidence_text TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 50. job_tailored_questions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_tailored_questions (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                requirement_id TEXT,
                question_text TEXT NOT NULL,
                category TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                quality_score REAL DEFAULT 8.0,
                evaluation_metrics TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 51. achievement_definitions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS achievement_definitions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                trigger_event TEXT NOT NULL,
                condition_type TEXT NOT NULL,
                threshold_value REAL NOT NULL,
                badge_icon TEXT NOT NULL,
                reward_points INTEGER DEFAULT 50,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)

        # 52. user_achievements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                achievement_id TEXT NOT NULL,
                triggering_event_id TEXT,
                unlocked_at TEXT NOT NULL,
                reward_claimed INTEGER DEFAULT 0,
                metadata_json TEXT,
                UNIQUE(user_id, achievement_id)
            )
        """)

        # 53. performance_snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_snapshots (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                snapshot_type TEXT NOT NULL,
                overall_readiness REAL NOT NULL,
                category_scores_json TEXT NOT NULL,
                sample_counts_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # 54. job_assessment_sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_assessment_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                job_id TEXT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                experience_level TEXT DEFAULT 'Fresher',
                target_date TEXT,
                raw_jd_text TEXT,
                status TEXT DEFAULT 'IN_PROGRESS',
                overall_readiness REAL,
                assessment_coverage REAL DEFAULT 0.0,
                evidence_confidence REAL DEFAULT 0.0,
                readiness_status TEXT DEFAULT 'READINESS NOT YET ESTABLISHED',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 55. job_requirement_snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_requirement_snapshots (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                job_id TEXT,
                canonical_skill_id TEXT NOT NULL,
                original_source_text TEXT,
                normalized_description TEXT NOT NULL,
                requirement_type TEXT NOT NULL,
                importance REAL DEFAULT 3.0,
                role_relevance REAL DEFAULT 1.0,
                evidence_source TEXT DEFAULT 'job_description',
                extraction_confidence REAL DEFAULT 0.9,
                created_at TEXT NOT NULL
            )
        """)

        # 56. assessment_blueprints
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assessment_blueprints (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                role_tier TEXT DEFAULT 'mid',
                planned_components_json TEXT NOT NULL,
                target_skills_json TEXT NOT NULL,
                weights_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # 57. assessment_attempts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assessment_attempts (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                component_type TEXT NOT NULL,
                question_id TEXT NOT NULL,
                canonical_skill_id TEXT NOT NULL,
                candidate_response TEXT,
                code_submission TEXT,
                time_taken_seconds INTEGER DEFAULT 0,
                status TEXT DEFAULT 'COMPLETED',
                created_at TEXT NOT NULL
            )
        """)

        # 58. assessment_evaluations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assessment_evaluations (
                id TEXT PRIMARY KEY,
                attempt_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                canonical_skill_id TEXT NOT NULL,
                correctness_score REAL NOT NULL,
                depth_score REAL NOT NULL,
                communication_score REAL NOT NULL,
                overall_score REAL NOT NULL,
                rubric_breakdown_json TEXT NOT NULL,
                feedback TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 59. readiness_snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS readiness_snapshots (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                overall_readiness REAL,
                readiness_status TEXT NOT NULL,
                assessment_coverage REAL NOT NULL,
                evidence_confidence REAL NOT NULL,
                mandatory_readiness REAL DEFAULT 0.0,
                preferred_readiness REAL DEFAULT 0.0,
                coding_readiness REAL DEFAULT 0.0,
                interview_readiness REAL DEFAULT 0.0,
                practical_readiness REAL DEFAULT 0.0,
                resume_alignment REAL DEFAULT 0.0,
                project_relevance REAL DEFAULT 0.0,
                comm_behavioral REAL DEFAULT 0.0,
                dimension_scores_json TEXT NOT NULL,
                limitations_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # 60. job_recommendations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_recommendations (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                canonical_skill_id TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                problem_identified TEXT NOT NULL,
                supporting_evidence TEXT NOT NULL,
                target_competency TEXT NOT NULL,
                priority TEXT NOT NULL,
                recommended_practice TEXT NOT NULL,
                relevant_activity TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 61. topic_assignment_progress (Strict Assignment Question Coverage per Topic)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topic_assignment_progress (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                topic_id TEXT NOT NULL,
                total_required_questions INTEGER NOT NULL DEFAULT 5,
                completed_question_ids_json TEXT NOT NULL DEFAULT '[]',
                completed_count INTEGER NOT NULL DEFAULT 0,
                coverage_percentage REAL NOT NULL DEFAULT 0.0,
                is_fully_covered INTEGER NOT NULL DEFAULT 0,
                average_assignment_score REAL NOT NULL DEFAULT 0.0,
                last_attempted_at TEXT,
                updated_at TEXT NOT NULL
            )
        """)

        # 62. candidate_intelligence_snapshots (Immutable Historical Snapshots)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidate_intelligence_snapshots (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                target_role TEXT NOT NULL,
                target_company TEXT,
                overall_readiness REAL,
                readiness_status TEXT NOT NULL,
                assessment_coverage REAL NOT NULL,
                evidence_confidence TEXT NOT NULL,
                resume_quality_score REAL NOT NULL,
                jd_alignment_score REAL NOT NULL,
                ava_interview_score REAL NOT NULL,
                coding_score REAL NOT NULL,
                project_experience_score REAL NOT NULL,
                communication_score REAL NOT NULL,
                consistency_score REAL NOT NULL,
                major_strengths_json TEXT NOT NULL,
                major_gaps_json TEXT NOT NULL,
                improvement_deltas_json TEXT NOT NULL,
                coaching_recommendations_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Seed Default Achievements
        cursor.execute("SELECT COUNT(*) FROM achievement_definitions")
        if cursor.fetchone()[0] == 0:
            default_achievements = [
                ("first_flight", "First Flight", "Completed your first Ava AI mock interview session.", "activity", "interview_completed", "count_gte", 1.0, "Award", 50),
                ("interview_veteran_5", "Interview Veteran", "Completed 5 comprehensive interview simulations.", "activity", "interview_completed", "count_gte", 5.0, "Trophy", 100),
                ("code_runner_10", "Code Runner", "Successfully solved 10 coding challenges in the sandbox.", "activity", "coding_attempt_completed", "count_gte", 10.0, "Terminal", 100),
                ("algo_specialist_50", "Algorithm Specialist", "Successfully passed 50 coding challenge submissions.", "activity", "coding_attempt_completed", "count_gte", 50.0, "Cpu", 250),
                ("high_performer_85", "High Performer", "Scored 85% or higher on an interview or technical assessment.", "proficiency", "assessment_completed", "score_gte", 85.0, "Zap", 150),
                ("rapid_improver_15", "Rapid Improver", "Increased your verified baseline performance by +15% or more.", "improvement", "improvement_analyzed", "delta_gte", 15.0, "TrendingUp", 200),
                ("target_ready", "Target Ready", "Analyzed a job description and created a tailored preparation plan.", "activity", "job_description_analyzed", "count_gte", 1.0, "Target", 75),
                ("roadmap_pioneer", "Roadmap Pioneer", "Completed your first personalized roadmap activity.", "activity", "roadmap_task_completed", "count_gte", 1.0, "Compass", 50),
                ("consistent_learner_7", "Consistent Learner", "Completed 7 roadmap activities on schedule.", "streak", "roadmap_task_completed", "count_gte", 7.0, "Flame", 150),
                ("gap_closer", "Gap Closer", "Closed a critical skill gap required for your target job.", "mastery", "skill_gap_closed", "count_gte", 1.0, "CheckCircle2", 150)
            ]
            for ach in default_achievements:
                cursor.execute("""
                    INSERT INTO achievement_definitions
                    (id, name, description, category, trigger_event, condition_type, threshold_value, badge_icon, reward_points, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (*ach, datetime.utcnow().isoformat()))

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
                generate_password_hash("mock_sa_pass_2026"),
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
                "mock_local_key",
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
                generate_password_hash("mock_org_admin_pass_2026"),
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
        return QueryBuilder(self, _validate_ident(name))


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
        self.table_name = _validate_ident(table_name)
        self.filters = []
        self.order_by = None
        self.limit_val = None
        self.operation = None
        self.data_to_write = None
        self.on_conflict = None
        self._maybe_single = False

    def select(self, columns="*", count=None):
        self.operation = "select"
        if columns and columns != "*":
            for c in str(columns).split(","):
                c_clean = c.strip()
                if c_clean:
                    _validate_ident(c_clean)
        self.columns = columns
        self.count_opt = count
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
        self.filters.append(("eq", _validate_ident(column), value))
        return self

    def neq(self, column, value):
        self.filters.append(("neq", _validate_ident(column), value))
        return self

    def in_(self, column, values):
        self.filters.append(("in", _validate_ident(column), values))
        return self

    def gte(self, column, value):
        self.filters.append(("gte", _validate_ident(column), value))
        return self

    def gt(self, column, value):
        self.filters.append(("gt", _validate_ident(column), value))
        return self

    def lt(self, column, value):
        self.filters.append(("lt", _validate_ident(column), value))
        return self

    def lte(self, column, value):
        self.filters.append(("lte", _validate_ident(column), value))
        return self

    def like(self, column, pattern):
        self.filters.append(("like", _validate_ident(column), pattern))
        return self

    def ilike(self, column, pattern):
        self.filters.append(("ilike", _validate_ident(column), pattern))
        return self

    def is_(self, column, value):
        self.filters.append(("is", _validate_ident(column), value))
        return self

    def order(self, column, desc=False):
        self.order_by = (_validate_ident(column), desc)
        return self

    def limit(self, value):
        self.limit_val = value
        return self

    def maybe_single(self):
        self._maybe_single = True
        return self

    def or_(self, filter_expr):
        self.filters.append(("or", filter_expr, None))
        return self


    def execute(self):
        conn = self.client._get_conn()
        try:
            return self._execute_internal(conn)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _execute_internal(self, conn):
        cursor = conn.cursor()
        
        # Get list of columns in the SQLite table dynamically
        cursor.execute(f"PRAGMA table_info({self.table_name})")
        columns_info = cursor.fetchall()
        table_cols = [info[1] for info in columns_info]
        integer_cols = [info[1] for info in columns_info if "INT" in info[2].upper()]
        
        filter_parts = []
        params = []
        for op, col, val in self.filters:
            valid_col = _validate_ident(col) if op != "or" else None
            if op == "eq":
                filter_parts.append(f"{valid_col} = ?")
                params.append(val)
            elif op == "neq":
                filter_parts.append(f"{valid_col} != ?")
                params.append(val)
            elif op == "gte":
                filter_parts.append(f"{valid_col} >= ?")
                params.append(val)
            elif op == "gt":
                filter_parts.append(f"{valid_col} > ?")
                params.append(val)
            elif op == "lt":
                filter_parts.append(f"{valid_col} < ?")
                params.append(val)
            elif op == "lte":
                filter_parts.append(f"{valid_col} <= ?")
                params.append(val)
            elif op in ("like", "ilike"):
                filter_parts.append(f"{valid_col} LIKE ?")
                params.append(val)
            elif op == "is":
                if val is None:
                    filter_parts.append(f"{valid_col} IS NULL")
                else:
                    filter_parts.append(f"{valid_col} IS ?")
                    params.append(val)
            elif op == "in":
                placeholders = ",".join("?" for _ in val)
                filter_parts.append(f"{valid_col} IN ({placeholders})")
                params.extend(val)
            elif op == "or":
                sub_parts = []
                for sub in col.split(","):
                    sub_clean = sub.strip()
                    matched = False
                    for postgrest_op, sql_op in [
                        (".eq.", "="), (".neq.", "!="), (".gte.", ">="),
                        (".gt.", ">"), (".lte.", "<="), (".lt.", "<"),
                        (".like.", "LIKE"), (".ilike.", "LIKE"), (".is.", "IS")
                    ]:
                        if postgrest_op in sub_clean:
                            c, v = sub_clean.split(postgrest_op, 1)
                            sub_parts.append(f"{_validate_ident(c.strip())} {sql_op} ?")
                            params.append(v.strip())
                            matched = True
                            break
                    if not matched and ".eq." in sub_clean:
                        c, v = sub_clean.split(".eq.", 1)
                        sub_parts.append(f"{_validate_ident(c.strip())} = ?")
                        params.append(v.strip())
                if sub_parts:
                    filter_parts.append("(" + " OR ".join(sub_parts) + ")")

                
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
                cols = ",".join(_validate_ident(c.strip()) for c in cols.split(","))
            
            sql = f"SELECT {cols} FROM {self.table_name} {where_clause}"
            if self.order_by:
                col, desc = self.order_by
                sql += f" ORDER BY {col} {'DESC' if desc else 'ASC'}"
            if self.limit_val:
                sql += f" LIMIT {int(self.limit_val)}"
                
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
                
                for k in list(item.keys()):
                    valid_k = _validate_ident(k)
                    if valid_k not in table_cols:
                        try:
                            cursor.execute(f"ALTER TABLE {self.table_name} ADD COLUMN {valid_k} TEXT")
                            table_cols.append(valid_k)
                        except Exception:
                            pass

                keys = [_validate_ident(k) for k in item.keys() if k in table_cols]
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

            for k in list(item.keys()):
                valid_k = _validate_ident(k)
                if valid_k not in table_cols:
                    try:
                        cursor.execute(f"ALTER TABLE {self.table_name} ADD COLUMN {valid_k} TEXT")
                        table_cols.append(valid_k)
                    except Exception:
                        pass
            
            keys = [_validate_ident(k) for k in item.keys() if k in table_cols]
            set_parts = [f"{_validate_ident(k)} = ?" for k in keys]
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
                    raw_conflicts = [self.on_conflict] if isinstance(self.on_conflict, str) else list(self.on_conflict)
                    conflict_cols = [_validate_ident(c) for c in raw_conflicts]
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
                    elif self.table_name in ["super_admin", "admin", "organization", "students"]:
                        conflict_cols = ["email"] if "email" in item else ["id"]
                
                for k in list(item.keys()):
                    valid_k = _validate_ident(k)
                    if valid_k not in table_cols:
                        try:
                            cursor.execute(f"ALTER TABLE {self.table_name} ADD COLUMN {valid_k} TEXT")
                            table_cols.append(valid_k)
                        except Exception:
                            pass

                exists = False
                exist_filters = []
                exist_params = []
                for col in conflict_cols:
                    valid_col = _validate_ident(col)
                    if valid_col in item:
                        exist_filters.append(f"{valid_col} = ?")
                        exist_params.append(item[valid_col])
                
                if exist_filters:
                    check_sql = f"SELECT * FROM {self.table_name} WHERE " + " AND ".join(exist_filters)
                    cursor.execute(check_sql, exist_params)
                    row = cursor.fetchone()
                    if row:
                        exists = True
                
                if exists:
                    if "updated_at" in table_cols and "updated_at" not in item:
                        item["updated_at"] = datetime.utcnow().isoformat()
                    keys = [_validate_ident(k) for k in item.keys() if k not in conflict_cols and k in table_cols]
                    if keys:
                        set_parts = [f"{_validate_ident(k)} = ?" for k in keys]
                        vals = [serialize_val(item[k]) for k in keys]
                        update_sql = f"UPDATE {self.table_name} SET {','.join(set_parts)} WHERE " + " AND ".join(exist_filters)
                        cursor.execute(update_sql, vals + exist_params)
                else:
                    if "created_at" in table_cols and "created_at" not in item:
                        item["created_at"] = datetime.utcnow().isoformat()
                    keys = [_validate_ident(k) for k in item.keys() if k in table_cols]
                    vals = [serialize_val(item[k]) for k in keys]
                    placeholders = ",".join("?" for _ in keys)
                    insert_sql = f"INSERT INTO {self.table_name} ({','.join(keys)}) VALUES ({placeholders})"
                    cursor.execute(insert_sql, vals)
                
                if exist_filters:
                    cursor.execute(f"SELECT * FROM {self.table_name} WHERE " + " AND ".join(exist_filters), exist_params)
                    r = cursor.fetchone()
                    if r:
                        upserted_rows.append(deserialize_row(r))
            
            conn.commit()
            result_data = upserted_rows
        return DummyResult(result_data)

try:
    SQLiteSupabaseMock()
except Exception as e:
    print("Auto DB init notice:", e)
_default_mock_client = None

def get_supabase_client():
    global _default_mock_client
    if _default_mock_client is None:
        _default_mock_client = SQLiteSupabaseMock()
    return _default_mock_client
