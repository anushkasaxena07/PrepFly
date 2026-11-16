"""
PREPFLY PHASE 4 UNIT TESTS: ADAPTIVE DIAGNOSTIC ENGINE & GRADING PIPELINE
========================================================================
Validates Section 4 and Section 11 of the Full Build Specification:
1. Starting difficulty by level (Junior=EASY, Mid=MEDIUM, Staff=HARD).
2. Dynamic difficulty stepping (>=75 step up, 40-74 stay, <40 step down).
3. Question ordering: MANDATORY (highest importance first), then PREFERRED.
4. Skill stop condition: >= 2 graded answers across >= 2 different subskills.
5. Grading pipeline: MCQ deterministic, SHORT_ANSWER rubric evaluation.
6. Golden Rule 1: Code computes the score from rubric points awarded.
7. Dual-run variance check (>15 pt difference triggers 3rd run and median).
8. Blank or <10 char answers marked SKIPPED, not counted as gap evidence.
9. Result Screen payload (Section 4.4 format and mandatory summary sentence).
10. API endpoints: POST /api/assessment/start, /answer, and /finish.
"""

import unittest
import os
import json

os.environ["ENVIRONMENT"] = "test"
os.environ["FLASK_ENV"] = "test"

from services.diagnostic_engine import (
    DiagnosticEngine,
    STARTING_DIFFICULTY_BY_LEVEL,
    DIFFICULTY_STEPS,
    CURATED_DIAGNOSTIC_QUESTIONS
)
from services.onboarding_service import OnboardingService
from app import app


class TestPhase4DiagnosticEngine(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_01_starting_difficulty_by_experience_level(self):
        """4.2 Starting difficulty: JUNIOR=EASY, MID=MEDIUM, SENIOR=MEDIUM, STAFF=HARD."""
        self.assertEqual(STARTING_DIFFICULTY_BY_LEVEL["JUNIOR"], "EASY")
        self.assertEqual(STARTING_DIFFICULTY_BY_LEVEL["MID"], "MEDIUM")
        self.assertEqual(STARTING_DIFFICULTY_BY_LEVEL["SENIOR"], "MEDIUM")
        self.assertEqual(STARTING_DIFFICULTY_BY_LEVEL["STAFF"], "HARD")

        # Test session initialization reflects user level starting difficulty
        OnboardingService._PROFILE_CACHE["user_jr_test"] = {"level": "JUNIOR"}
        session_jr = DiagnosticEngine.start_diagnostic_session(user_id="user_jr_test")
        self.assertEqual(session_jr["first_question"]["difficulty"], "EASY")

        OnboardingService._PROFILE_CACHE["user_staff_test"] = {"level": "STAFF"}
        session_staff = DiagnosticEngine.start_diagnostic_session(user_id="user_staff_test")
        # Starts with HARD for staff level if available
        first_q = session_staff["first_question"]
        self.assertIsNotNone(first_q)

    def test_02_dynamic_difficulty_stepping(self):
        """4.2 Score >= 75 -> step up; 40-74 -> stay; < 40 -> step down."""
        # Create session with MID (starting MEDIUM)
        OnboardingService._PROFILE_CACHE["user_step_test"] = {"level": "MID"}
        session_data = DiagnosticEngine.start_diagnostic_session(user_id="user_step_test")
        sid = session_data["session_id"]
        state = DiagnosticEngine._ACTIVE_SESSIONS[sid]

        sk_id = "python_ml"
        state["current_difficulty_by_skill"][sk_id] = "MEDIUM"

        # Case 1: Score >= 75 -> step up to HARD
        dummy_q = {
            "id": "q_step_up",
            "skillId": sk_id,
            "subskillId": "vectorisation",
            "difficulty": "MEDIUM",
            "type": "MCQ",
            "options": ["A", "B"],
            "correctOptions": [0],
            "rubric": [{"id": "r1", "points": 100}]
        }
        CURATED_DIAGNOSTIC_QUESTIONS.append(dummy_q)
        try:
            # Answer correctly -> score 100
            res = DiagnosticEngine.submit_diagnostic_answer(
                session_id=sid,
                question_id="q_step_up",
                answer_text="0",
                selected_options=[0]
            )
            self.assertEqual(res["score"], 100.0)
            self.assertEqual(state["current_difficulty_by_skill"][sk_id], "HARD")

            # Case 2: Score < 40 -> step down back to MEDIUM
            dummy_q2 = {
                "id": "q_step_down",
                "skillId": sk_id,
                "subskillId": "broadcasting",
                "difficulty": "HARD",
                "type": "MCQ",
                "options": ["A", "B"],
                "correctOptions": [0],
                "rubric": [{"id": "r1", "points": 100}]
            }
            CURATED_DIAGNOSTIC_QUESTIONS.append(dummy_q2)
            res2 = DiagnosticEngine.submit_diagnostic_answer(
                session_id=sid,
                question_id="q_step_down",
                answer_text="1",
                selected_options=[1]
            )
            self.assertEqual(res2["score"], 0.0)
            self.assertEqual(state["current_difficulty_by_skill"][sk_id], "MEDIUM")
        finally:
            if dummy_q in CURATED_DIAGNOSTIC_QUESTIONS:
                CURATED_DIAGNOSTIC_QUESTIONS.remove(dummy_q)
            if dummy_q2 in CURATED_DIAGNOSTIC_QUESTIONS:
                CURATED_DIAGNOSTIC_QUESTIONS.remove(dummy_q2)

    def test_03_question_ordering_and_no_immediate_subskill_repeat(self):
        """4.1 & 4.2: MANDATORY first by importance; never ask same subskill twice in row."""
        target_skills = [
            {"id": "sk_pref", "name": "Preferred Skill", "tier": "PREFERRED", "importance": 4, "subskills": ["sub_p1"]},
            {"id": "sk_mand_low", "name": "Mandatory Low", "tier": "MANDATORY", "importance": 3, "subskills": ["sub_m1"]},
            {"id": "sk_mand_high", "name": "Mandatory High", "tier": "MANDATORY", "importance": 5, "subskills": ["sub_m2_a", "sub_m2_b"]}
        ]

        dummy_questions = [
            {"id": "q_pref", "skillId": "sk_pref", "subskillId": "sub_p1", "difficulty": "MEDIUM", "type": "MCQ", "options": ["A"], "correctOptions": [0], "rubric": []},
            {"id": "q_m_low", "skillId": "sk_mand_low", "subskillId": "sub_m1", "difficulty": "MEDIUM", "type": "MCQ", "options": ["A"], "correctOptions": [0], "rubric": []},
            {"id": "q_m_high_1", "skillId": "sk_mand_high", "subskillId": "sub_m2_a", "difficulty": "MEDIUM", "type": "MCQ", "options": ["A"], "correctOptions": [0], "rubric": []},
            {"id": "q_m_high_2", "skillId": "sk_mand_high", "subskillId": "sub_m2_a", "difficulty": "MEDIUM", "type": "MCQ", "options": ["A"], "correctOptions": [0], "rubric": []},
            {"id": "q_m_high_3", "skillId": "sk_mand_high", "subskillId": "sub_m2_b", "difficulty": "MEDIUM", "type": "MCQ", "options": ["A"], "correctOptions": [0], "rubric": []}
        ]

        CURATED_DIAGNOSTIC_QUESTIONS.extend(dummy_questions)
        try:
            session_state = {
                "asked_question_ids": [],
                "skills_profile": target_skills,
                "current_difficulty_by_skill": {"sk_pref": "MEDIUM", "sk_mand_low": "MEDIUM", "sk_mand_high": "MEDIUM"},
                "subskills_tested_by_skill": {},
                "graded_answers_by_skill": {},
                "last_subskill_asked": None
            }

            # 1. First question must be from sk_mand_high (MANDATORY with highest importance 5)
            first_q = DiagnosticEngine.select_next_question(session_state)
            self.assertEqual(first_q["skillId"], "sk_mand_high")

            # Mark sub_m2_a as last asked
            session_state["asked_question_ids"].append(first_q["id"])
            session_state["last_subskill_asked"] = "sub_m2_a"

            # 2. Next question must NOT be sub_m2_a (no repeat of same subskill in row)
            second_q = DiagnosticEngine.select_next_question(session_state)
            self.assertNotEqual(second_q["subskillId"], "sub_m2_a")
        finally:
            for q in dummy_questions:
                if q in CURATED_DIAGNOSTIC_QUESTIONS:
                    CURATED_DIAGNOSTIC_QUESTIONS.remove(q)

    def test_04_skill_stop_condition(self):
        """4.2 Stop asking a skill when >= 2 graded answers across >= 2 different subskills."""
        target_skills = [
            {"id": "sk_stop_test", "name": "Stop Test Skill", "tier": "MANDATORY", "importance": 5, "subskills": ["sub_1", "sub_2"]},
            {"id": "sk_other", "name": "Other Skill", "tier": "PREFERRED", "importance": 3, "subskills": ["sub_3"]}
        ]

        session_state = {
            "asked_question_ids": ["q1", "q2"],
            "skills_profile": target_skills,
            "current_difficulty_by_skill": {"sk_stop_test": "MEDIUM", "sk_other": "MEDIUM"},
            # Has 2 graded answers across 2 different subskills:
            "subskills_tested_by_skill": {"sk_stop_test": {"sub_1", "sub_2"}},
            "graded_answers_by_skill": {"sk_stop_test": [80.0, 85.0]},
            "last_subskill_asked": "sub_2"
        }

        dummy_q_other = {
            "id": "q_other_01",
            "skillId": "sk_other",
            "subskillId": "sub_3",
            "difficulty": "MEDIUM",
            "type": "MCQ",
            "options": ["A"],
            "correctOptions": [0],
            "rubric": []
        }
        CURATED_DIAGNOSTIC_QUESTIONS.append(dummy_q_other)
        try:
            # Should skip sk_stop_test and select from sk_other
            next_q = DiagnosticEngine.select_next_question(session_state)
            self.assertEqual(next_q["skillId"], "sk_other")
        finally:
            if dummy_q_other in CURATED_DIAGNOSTIC_QUESTIONS:
                CURATED_DIAGNOSTIC_QUESTIONS.remove(dummy_q_other)

    def test_05_blank_or_under_10_char_answer_marked_skipped(self):
        """4.3 & Golden Rule 4: Blank or <10 chars -> score 0, attempted=false, SKIPPED, not weakness."""
        q = {
            "id": "q_short_test",
            "skillId": "python_ml",
            "type": "SHORT_ANSWER",
            "rubric": [{"id": "r1", "criterion": "Detailed explanation", "points": 100}]
        }

        # Sub 10-char answer
        res_short = DiagnosticEngine.grade_answer(q, answer_text="too short")
        self.assertEqual(res_short["score"], 0.0)
        self.assertFalse(res_short["is_attempted"])
        self.assertEqual(res_short["status"], "SKIPPED")
        self.assertEqual(res_short["failed_rubrics"], [])

        # Blank answer
        res_blank = DiagnosticEngine.grade_answer(q, answer_text="   ")
        self.assertEqual(res_blank["score"], 0.0)
        self.assertFalse(res_blank["is_attempted"])
        self.assertEqual(res_blank["status"], "SKIPPED")

    def test_06_mcq_deterministic_grading(self):
        """4.3 MCQ auto-graded deterministically."""
        mcq_q = {
            "id": "q_mcq_test",
            "skillId": "supervised_learning",
            "type": "MCQ",
            "options": ["Option 0", "Option 1 (Correct)", "Option 2"],
            "correctOptions": [1],
            "rubric": [{"id": "r1", "points": 100, "criterion": "Correct option selected"}]
        }

        # Correct answer
        grade_correct = DiagnosticEngine.grade_answer(mcq_q, selected_options=[1])
        self.assertEqual(grade_correct["score"], 100.0)
        self.assertTrue(grade_correct["is_attempted"])
        self.assertEqual(grade_correct["status"], "GRADED")

        # Incorrect answer
        grade_wrong = DiagnosticEngine.grade_answer(mcq_q, selected_options=[2])
        self.assertEqual(grade_wrong["score"], 0.0)
        self.assertTrue(grade_wrong["is_attempted"])
        self.assertEqual(len(grade_wrong["failed_rubrics"]), 1)

    def test_07_code_computes_score_from_rubric_points(self):
        """Golden Rule 1: Code computes the score from rubric points awarded."""
        rubric_items = [
            {"id": "r1", "points": 40, "criterion": "Item 1"},
            {"id": "r2", "points": 35, "criterion": "Item 2"},
            {"id": "r3", "points": 25, "criterion": "Item 3"}
        ]
        grader_items = [
            {"rubricId": "r1", "result": "PASS", "pointsAwarded": 40},
            {"rubricId": "r2", "result": "PARTIAL", "pointsAwarded": 17},
            {"rubricId": "r3", "result": "FAIL", "pointsAwarded": 0}
        ]

        score, failures = DiagnosticEngine._compute_rubric_score_and_failures(grader_items, rubric_items)
        expected_score = round((57.0 / 100.0) * 100.0, 1)
        self.assertEqual(score, expected_score)
        self.assertIn("Item 3", failures)

    def test_08_dual_run_variance_check_median(self):
        """4.3 If score difference > 15 between dual runs, run 3rd and take median."""
        q = {
            "id": "q_variance_test",
            "skillId": "python_ml",
            "type": "SHORT_ANSWER",
            "prompt": "Test prompt",
            "rubric": [{"id": "r1", "points": 100, "criterion": "Comprehensive test explanation"}]
        }

        original_eval = DiagnosticEngine._evaluate_rubric_with_llm
        call_count = [0]

        def mock_eval(question, answer, rubrics):
            call_count[0] += 1
            if call_count[0] == 1:
                return [{"rubricId": "r1", "result": "PASS", "pointsAwarded": 90}]
            elif call_count[0] == 2:
                # Difference is 90 - 60 = 30 > 15
                return [{"rubricId": "r1", "result": "PARTIAL", "pointsAwarded": 60}]
            else:
                # 3rd run
                return [{"rubricId": "r1", "result": "PARTIAL", "pointsAwarded": 75}]

        DiagnosticEngine._evaluate_rubric_with_llm = staticmethod(mock_eval)
        try:
            res = DiagnosticEngine.grade_answer(q, answer_text="Valid length answer exceeding ten characters.")
            self.assertEqual(call_count[0], 3)
            # Median of 90, 60, 75 is 75.0
            self.assertEqual(res["score"], 75.0)
        finally:
            DiagnosticEngine._evaluate_rubric_with_llm = original_eval

    def test_09_result_screen_payload_and_mandatory_sentence(self):
        """4.4 Result Screen format and mandatory summary sentence."""
        session_data = DiagnosticEngine.start_diagnostic_session(user_id="user_result_test")
        sid = session_data["session_id"]

        # Submit one valid answer and one skipped answer
        DiagnosticEngine.submit_diagnostic_answer(
            session_id=sid,
            question_id="q_py_vec_01",
            answer_text="NumPy vectorised operations run in compiled C code with contiguous memory and SIMD registers."
        )
        DiagnosticEngine.submit_diagnostic_answer(
            session_id=sid,
            question_id="q_py_broad_02",
            answer_text="skip"  # < 10 chars -> SKIPPED
        )

        res_screen = DiagnosticEngine.finish_diagnostic_session(sid)
        self.assertEqual(res_screen["status"], "success")
        self.assertIn("demonstrated_competency_pct", res_screen)
        self.assertIn("measurement_confidence_pct", res_screen)
        self.assertIn("curriculum_coverage_pct", res_screen)
        self.assertIn("assessment_completion_pct", res_screen)

        # Check mandatory summary sentence:
        sentence = res_screen["summary_sentence"]
        self.assertTrue("You were assessed on" in sentence)
        self.assertTrue("skills are not yet assessed and are not counted as weaknesses." in sentence)

    def test_10_api_endpoints_start_answer_finish(self):
        """Section 11 Endpoints: POST /api/assessment/start, /answer, /finish."""
        # 1. Start assessment
        res_start = self.app.post(
            "/api/assessment/start",
            json={"kind": "DIAGNOSTIC", "target_role": "AI/ML Engineer"},
            headers={"X-User-Id": "api_test_user"}
        )
        self.assertEqual(res_start.status_code, 200)
        data_start = res_start.get_json()
        self.assertEqual(data_start["status"], "success")
        sid = data_start["session_id"]
        first_q = data_start["first_question"]
        self.assertIsNotNone(sid)
        self.assertIsNotNone(first_q)

        # 2. Answer question
        res_ans = self.app.post(
            "/api/assessment/answer",
            json={
                "sessionId": sid,
                "questionId": first_q["id"],
                "answer": "NumPy vectorised operations execute in compiled C code with SIMD and contiguous memory layout.",
                "selectedOptions": []
            },
            headers={"X-User-Id": "api_test_user"}
        )
        self.assertEqual(res_ans.status_code, 200)
        data_ans = res_ans.get_json()
        self.assertEqual(data_ans["status"], "success")
        self.assertGreater(data_ans["score"], 0.0)

        # 3. Finish assessment
        res_fin = self.app.post(
            "/api/assessment/finish",
            json={"sessionId": sid},
            headers={"X-User-Id": "api_test_user"}
        )
        self.assertEqual(res_fin.status_code, 200)
        data_fin = res_fin.get_json()
        self.assertEqual(data_fin["status"], "success")
        self.assertIn("summary_sentence", data_fin)
        self.assertIn("readiness", data_fin)


if __name__ == "__main__":
    unittest.main()

