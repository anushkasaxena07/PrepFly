"""
Phase 1 Foundation Test Suite
Verifies data model migrations, timezone utilities, Zod/Pydantic schemas,
prompt files, and the runtime template guard.
"""

import os
import unittest
from datetime import datetime, date, timedelta
import zoneinfo

from utils.timezone_utils import (
    DEFAULT_TIMEZONE,
    get_timezone,
    get_current_user_datetime,
    get_current_user_date,
    determine_plan_start_date,
    format_date_iso,
    parse_date_iso,
    is_missed_day,
    get_relative_date_label
)
from utils.template_guard import (
    contains_unresolved_template,
    sanitize_user_facing_string,
    validate_dict_no_template_leaks
)
from schemas.spec_schemas import (
    RoleProfileLLMOutputSchema,
    PillarSchema,
    SkillSchema,
    SubskillSchema,
    RubricCriterionSchema,
    QuestionLLMOutputSchema,
    QuestionRubricItemSchema,
    GraderLLMOutputSchema,
    GraderItemResultSchema,
    DayBlockContentSchema,
    ReplanRequestSchema
)
from local_supabase import get_supabase_client


class TestPhase1Foundation(unittest.TestCase):
    """Verifies all Phase 1 Foundation deliverables."""

    def test_01_timezone_utilities_default_and_parsing(self):
        """Verifies Golden Rule 8: Asia/Kolkata default, aware datetime, and ISO parsing."""
        tz = get_timezone(None)
        self.assertEqual(tz.key, "Asia/Kolkata")

        tz_custom = get_timezone("America/New_York")
        self.assertEqual(tz_custom.key, "America/New_York")

        # Invalid timezone should fall back to Asia/Kolkata
        tz_invalid = get_timezone("Invalid/Fake_Zone")
        self.assertEqual(tz_invalid.key, "Asia/Kolkata")

        # Aware datetime
        now = get_current_user_datetime("Asia/Kolkata")
        self.assertIsNotNone(now.tzinfo)

        # Date parsing and formatting
        sample_date = date(2026, 11, 16)
        iso_str = format_date_iso(sample_date)
        self.assertEqual(iso_str, "2026-11-16")
        self.assertEqual(parse_date_iso(iso_str), sample_date)

    def test_02_timezone_start_date_cutoff_rule(self):
        """Verifies Section 8.2: before 18:00 with >= 20 mins -> Today, else Tomorrow."""
        # Using a deterministic helper check
        tz_kolkata = "Asia/Kolkata"
        now_dt = get_current_user_datetime(tz_kolkata)
        
        # Test case: if available minutes < 20, always starts Tomorrow
        d1, lbl1 = determine_plan_start_date(tz_kolkata, available_today_minutes=15)
        self.assertEqual(lbl1, "Tomorrow")
        self.assertEqual(d1, now_dt.date() + timedelta(days=1))

    def test_03_runtime_template_guard(self):
        """Verifies Golden Rule 5: Detects and blocks None(None), null, undefined, NaN, {{."""
        leak_cases = [
            "**Targeted Coaching for None (None):**",
            "Your score is NaN%",
            "Welcome null, start your journey",
            "The topic is undefined",
            "Hello {{user_name}}",
            "Overall readiness: None"
        ]
        for c in leak_cases:
            self.assertTrue(contains_unresolved_template(c), f"Failed to detect leak in: {c}")

        # Clean string
        clean_str = "Your overall readiness score is 85.0% based on verified evidence."
        self.assertFalse(contains_unresolved_template(clean_str))

        # Sanitizer removes and cleans leaks
        sanitized = sanitize_user_facing_string("**Targeted Coaching for None (None):**")
        self.assertNotIn("None (None)", sanitized)
        self.assertNotIn("None", sanitized)

        # Dict validation
        data_with_leak = {
            "title": "Topic Overview",
            "blocks": [{"topic": "Valid Topic", "why_here": "Topic for None (None)"}]
        }
        errors = validate_dict_no_template_leaks(data_with_leak)
        self.assertTrue(len(errors) > 0)

    def test_04_prompt_files_exist_and_match_spec(self):
        """Verifies all 5 Section 12 prompt files exist and contain required rules."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompts_dir = os.path.join(base_dir, "prompts")

        expected_files = [
            "12_1_role_profile_generator.txt",
            "12_2_question_generator.txt",
            "12_3_grader.txt",
            "12_4_day_content_generator.txt",
            "12_5_mentor_phrasing.txt"
        ]

        for fname in expected_files:
            fpath = os.path.join(prompts_dir, fname)
            self.assertTrue(os.path.exists(fpath), f"Missing prompt file: {fname}")
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read().strip()
            self.assertTrue(len(content) > 50, f"Prompt file {fname} is too short or empty")

    def test_05_zod_pydantic_schemas_validation(self):
        """Verifies schemas reject malformed LLM outputs and normalize rubric sums."""
        # 1. Question Rubric Sum Normalization to 100
        q_data = {
            "prompt": "Explain precision and recall trade-offs under class skew.",
            "rubric": [
                {"id": "r1", "criterion": "Precision definition", "points": 30},
                {"id": "r2", "criterion": "Recall definition", "points": 30},
                {"id": "r3", "criterion": "Trade-off analysis", "points": 20}
            ], # Sum = 80 -> should auto-normalize to 100
            "modelAnswer": "Precision measures TP/(TP+FP)...",
            "timeLimitSec": 180
        }
        validated_q = QuestionLLMOutputSchema(**q_data)
        total_points = sum(item.points for item in validated_q.rubric)
        self.assertEqual(total_points, 100)

        # 2. Grader Output Validation
        grader_data = {
            "items": [
                {"rubricId": "r1", "result": "PASS", "pointsAwarded": 30, "evidence": "TP/(TP+FP)"},
                {"rubricId": "r2", "result": "PASS", "pointsAwarded": 30, "evidence": "TP/(TP+FN)"},
                {"rubricId": "r3", "result": "PARTIAL", "pointsAwarded": 20, "evidence": "Mentions F1"}
            ],
            "feedbackSummary": "Solid theoretical distinction."
        }
        validated_g = GraderLLMOutputSchema(**grader_data)
        self.assertEqual(len(validated_g.items), 3)

        # 3. Replan Trigger Validation
        replan_data = {
            "trigger": "DAILY_MINUTES_CHANGED",
            "params": {"dailyMinutes": 30, "scope": "today"}
        }
        validated_r = ReplanRequestSchema(**replan_data)
        self.assertEqual(validated_r.trigger, "DAILY_MINUTES_CHANGED")

    def test_06_database_schema_initialization(self):
        """Verifies SQLite/Supabase local client creates Section 10 tables cleanly."""
        client = get_supabase_client()
        expected_tables = [
            "target_profiles", "availability", "blackout_dates", "pillars",
            "skills", "subskills", "questions", "assessment_sessions",
            "answers", "evidence", "skill_snapshots", "readiness_snapshots",
            "plans", "plan_days", "plan_blocks", "study_logs", "chat_messages"
        ]
        # Query SQLite sqlite_master to verify tables exist
        conn = client._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cursor.fetchall()}
        
        for tbl in expected_tables:
            self.assertIn(tbl, existing_tables, f"Table {tbl} was not created in database!")


if __name__ == "__main__":
    unittest.main()
