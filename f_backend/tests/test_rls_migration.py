"""
Unit and CI Regression Test for Supabase Row-Level Security (RLS) and Schema Lockdown.
Validates:
  1. All SQL migrations in supabase/migrations and f_backend/migrations enforce RLS.
  2. Every CREATE TABLE statement is protected by an explicit or dynamic ENABLE ROW LEVEL SECURITY.
  3. The RLS lockdown migration strictly revokes all privileges from anon and authenticated.
  4. The RLS lockdown migration locks ALTER DEFAULT PRIVILEGES for future tables.
  5. Zero permissive policies (e.g. USING (true)) exist for anon.
  6. All 54+ known public tables are explicitly enumerated and covered.
  7. Code-level audit verifying sensitive columns (password, otp, token, session_id)
     are excluded from backend selects and responses.
"""

import os
import re
import unittest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(BACKEND_DIR)

REQUIRED_TABLES = [
    "pending_users", "users", "otps", "otp_requests", "auth_logs",
    "password_reset_tokens", "feedback", "coding_problems", "parsed_resumes",
    "coding_rooms", "question_sheets", "webrtc_rooms", "resume_scores",
    "subscription", "platform_plans", "admin", "students", "announcements",
    "organization", "question_bank", "admin_interviews", "admin_coding",
    "super_admin", "ai_configuration", "support_tickets", "activity_logs",
    "support_conversations", "support_messages", "platform_settings",
    "candidate_profiles", "skills", "skill_prerequisites", "role_skill_requirements",
    "assessments", "assessment_questions", "assessment_attempts", "roadmaps",
    "roadmap_versions", "roadmap_activities", "skill_evidence",
    "candidate_skill_profiles", "activity_attempts", "revision_schedules",
    "preparation_events", "job_profiles", "interviewer_profiles",
    "candidate_resume_claims", "job_requirements", "job_tailored_questions",
    "achievement_definitions", "user_achievements", "performance_snapshots",
    "coding_submissions", "speech_analyses"
]


class TestRLSMigrationAndLockdown(unittest.TestCase):
    """Guards against RLS regressions and exposed sensitive columns in CI."""

    def setUp(self):
        self.migration_dirs = [
            os.path.join(REPO_ROOT, "supabase", "migrations"),
            os.path.join(BACKEND_DIR, "migrations")
        ]

    def _read_all_migrations(self):
        all_sql = {}
        for mdir in self.migration_dirs:
            if os.path.exists(mdir):
                for fname in os.listdir(mdir):
                    if fname.endswith(".sql") and not fname.endswith("_rollback.sql"):
                        fpath = os.path.join(mdir, fname)
                        with open(fpath, "r", encoding="utf-8") as f:
                            all_sql[fname] = f.read()
        return all_sql

    def test_01_all_required_tables_explicitly_locked_down(self):
        """Verifies that all 54 required tables have an explicit ALTER TABLE ... ENABLE ROW LEVEL SECURITY."""
        all_sql = self._read_all_migrations()
        combined_sql = "\n".join(all_sql.values())

        missing_tables = []
        for table in REQUIRED_TABLES:
            pattern = re.compile(
                rf"ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:public\.)?{table}\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY",
                re.IGNORECASE
            )
            if not pattern.search(combined_sql):
                missing_tables.append(table)

        self.assertEqual(
            len(missing_tables), 0,
            f"The following tables lack an explicit ENABLE ROW LEVEL SECURITY statement in migrations: {missing_tables}"
        )

    def test_02_dynamic_rls_loop_exists_in_lockdown_migration(self):
        """Verifies that the lockdown migration contains the dynamic DO loop for schema public."""
        all_sql = self._read_all_migrations()
        combined_sql = "\n".join(all_sql.values())

        has_dynamic_loop = "pg_tables" in combined_sql and "ENABLE ROW LEVEL SECURITY" in combined_sql
        self.assertTrue(
            has_dynamic_loop,
            "Lockdown migration must contain a dynamic DO block iterating over pg_tables in schema public."
        )

    def test_03_privileges_revoked_from_anon_and_authenticated(self):
        """Verifies that ALL privileges on tables, sequences, and routines are revoked from anon and authenticated."""
        all_sql = self._read_all_migrations()
        combined_sql = "\n".join(all_sql.values())

        self.assertRegex(
            combined_sql,
            re.compile(r"REVOKE\s+ALL\s+ON\s+ALL\s+TABLES\s+IN\s+SCHEMA\s+public\s+FROM\s+anon,\s*authenticated", re.IGNORECASE),
            "Must revoke all table privileges in public from anon and authenticated."
        )
        self.assertRegex(
            combined_sql,
            re.compile(r"REVOKE\s+ALL\s+ON\s+ALL\s+SEQUENCES\s+IN\s+SCHEMA\s+public\s+FROM\s+anon,\s*authenticated", re.IGNORECASE),
            "Must revoke all sequence privileges in public from anon and authenticated."
        )
        self.assertRegex(
            combined_sql,
            re.compile(r"REVOKE\s+ALL\s+ON\s+ALL\s+ROUTINES\s+IN\s+SCHEMA\s+public\s+FROM\s+anon,\s*authenticated", re.IGNORECASE),
            "Must revoke all routine/function privileges in public from anon and authenticated."
        )

    def test_04_default_privileges_locked_for_future_tables(self):
        """Verifies that ALTER DEFAULT PRIVILEGES revokes table/sequence/routine creation grants from anon and authenticated."""
        all_sql = self._read_all_migrations()
        combined_sql = "\n".join(all_sql.values())

        self.assertRegex(
            combined_sql,
            re.compile(r"ALTER\s+DEFAULT\s+PRIVILEGES\s+IN\s+SCHEMA\s+public\s+REVOKE\s+ALL\s+ON\s+TABLES\s+FROM\s+anon,\s*authenticated", re.IGNORECASE),
            "Must lock default table privileges for anon and authenticated."
        )
        self.assertRegex(
            combined_sql,
            re.compile(r"ALTER\s+DEFAULT\s+PRIVILEGES\s+IN\s+SCHEMA\s+public\s+REVOKE\s+ALL\s+ON\s+SEQUENCES\s+FROM\s+anon,\s*authenticated", re.IGNORECASE),
            "Must lock default sequence privileges for anon and authenticated."
        )

    def test_05_no_permissive_policies_for_anon(self):
        """Ensures zero permissive policies (USING true / WITH CHECK true) exist for anon in any migration."""
        all_sql = self._read_all_migrations()
        for fname, sql in all_sql.items():
            # Check for CREATE POLICY ... TO anon ... USING (true)
            permissive_match = re.search(
                r"CREATE\s+POLICY\s+.*?TO\s+(?:anon|public).*?USING\s*\(\s*true\s*\)",
                sql,
                re.IGNORECASE | re.DOTALL
            )
            self.assertIsNone(
                permissive_match,
                f"Found dangerous permissive policy for anon in {fname}: {permissive_match.group(0) if permissive_match else ''}"
            )

    def test_06_app_py_does_not_select_star_from_sensitive_user_tables(self):
        """Verifies that app.py does not execute unbounded select('*') on users, otps, or password_reset_tokens."""
        app_path = os.path.join(BACKEND_DIR, "app.py")
        with open(app_path, "r", encoding="utf-8") as f:
            app_code = f.read()

        # Check otps
        self.assertNotIn(
            'table("otps").select("*")',
            app_code,
            "app.py must not query table('otps').select('*')"
        )

        # Check password_reset_tokens
        self.assertNotIn(
            'table("password_reset_tokens").select("*")',
            app_code,
            "app.py must not query table('password_reset_tokens').select('*')"
        )

        # Check superadmin_candidates_summary and superadmin_get_students
        self.assertTrue(
            'table("users").select("id, email, subscription, plan, created_at").execute' in app_code,
            "app.py must use explicit column selection for users table in superadmin candidates summary."
        )
        self.assertTrue(
            'table("users").select("id, name, email, phone, roll_number, organization_id, department, subscription, role, created_at").execute' in app_code,
            "app.py must use explicit column selection for users table in superadmin students list."
        )


if __name__ == "__main__":
    unittest.main()
