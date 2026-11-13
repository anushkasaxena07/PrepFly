"""
Comprehensive Regression Test Suite for PrepFly Ava AI Interview Engine
Implements all 16 mandatory automated validation tests specified in Section 6:
1. Resume Mode — DSA Selected
2. Resume Mode — System Design Selected
3. Resume Mode — Computer Science Fundamentals Selected
4. Resume Mode — HR & Behavioral Selected
5. Mixed Topics Rotation
6. Topic Validation & Rejection
7. Job Description Mode — Python Backend
8. Job Description Mode — Frontend
9. Job Description Mode — HR (Strictly Non-Technical)
10. Off-topic JD Rejection
11. Scoring — Completely Correct Answer
12. Scoring — Irrelevant / Off-topic Answer
13. Scoring — Non-Answer ("I don't know" / empty)
14. Scoring — Early Exit ("can i end inw")
15. Incomplete Interview Report Proration (< 5 answers)
16. Executive Summary Data Integrity & Metadata Isolation
"""

import unittest
import sys
import os

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services.topic_engine import (
    TOPIC_DSA,
    TOPIC_SYSTEM_DESIGN,
    TOPIC_CS_FUNDAMENTALS,
    TOPIC_HR_BEHAVIORAL,
    validate_topic_question,
    validate_jd_question,
    get_curated_fallback_question
)

from services.answer_classifier import (
    classify_candidate_response,
    extract_verified_strength,
    extract_verified_weakness,
    compute_deterministic_score,
    CLASS_CORRECT_COMPLETE,
    CLASS_PARTIALLY_CORRECT,
    CLASS_INCORRECT,
    CLASS_IRRELEVANT_OFF_TOPIC,
    CLASS_NO_ANSWER,
    CLASS_EARLY_EXIT,
    CLASS_UNCLEAR_INSUFFICIENT
)

from services.feedback_service import (
    evaluate_response_comprehensive,
    fast_compile_report
)

from services.ai_service import generate_dynamic_question


class TestInterviewPipelineComprehensive(unittest.TestCase):

    # ------------------------------------------------------------------------
    # 1. RESUME MODE — DSA SELECTED
    # ------------------------------------------------------------------------
    def test_01_resume_mode_dsa_only(self):
        allowed = [TOPIC_DSA]
        q1 = get_curated_fallback_question(2, allowed)
        q2 = get_curated_fallback_question(3, allowed, previous_questions=[q1])
        q3 = get_curated_fallback_question(4, allowed, previous_questions=[q1, q2])

        for q in [q1, q2, q3]:
            is_valid, matched, reason = validate_topic_question(q, allowed)
            self.assertTrue(is_valid, f"DSA question '{q}' rejected: {reason}")
            self.assertEqual(matched, TOPIC_DSA)

        # Off-topic checks: System design and HR questions must be rejected
        self.assertFalse(validate_topic_question("Design a distributed message broker", allowed)[0])
        self.assertFalse(validate_topic_question("Tell me about a time you handled conflict", allowed)[0])

    # ------------------------------------------------------------------------
    # 2. RESUME MODE — SYSTEM DESIGN SELECTED
    # ------------------------------------------------------------------------
    def test_02_resume_mode_system_design_only(self):
        allowed = [TOPIC_SYSTEM_DESIGN]
        q1 = get_curated_fallback_question(2, allowed)
        q2 = get_curated_fallback_question(3, allowed, previous_questions=[q1])

        for q in [q1, q2]:
            is_valid, matched, reason = validate_topic_question(q, allowed)
            self.assertTrue(is_valid, f"System Design question '{q}' rejected: {reason}")
            self.assertEqual(matched, TOPIC_SYSTEM_DESIGN)

        # Off-topic checks: Invert binary tree must be rejected
        self.assertFalse(validate_topic_question("Invert a binary tree in O(N) time", allowed)[0])

    # ------------------------------------------------------------------------
    # 3. RESUME MODE — COMPUTER SCIENCE FUNDAMENTALS SELECTED
    # ------------------------------------------------------------------------
    def test_03_resume_mode_cs_fundamentals_only(self):
        allowed = [TOPIC_CS_FUNDAMENTALS]
        q1 = get_curated_fallback_question(2, allowed)
        q2 = get_curated_fallback_question(3, allowed, previous_questions=[q1])

        for q in [q1, q2]:
            is_valid, matched, reason = validate_topic_question(q, allowed)
            self.assertTrue(is_valid, f"CS Fundamentals question '{q}' rejected: {reason}")
            self.assertEqual(matched, TOPIC_CS_FUNDAMENTALS)

        # HR and System design must be rejected
        self.assertFalse(validate_topic_question("Why do you want to join this company?", allowed)[0])

    # ------------------------------------------------------------------------
    # 4. RESUME MODE — HR & BEHAVIORAL SELECTED
    # ------------------------------------------------------------------------
    def test_04_resume_mode_hr_behavioral_only(self):
        allowed = [TOPIC_HR_BEHAVIORAL]
        q1 = get_curated_fallback_question(2, allowed)
        q2 = get_curated_fallback_question(3, allowed, previous_questions=[q1])

        for q in [q1, q2]:
            is_valid, matched, reason = validate_topic_question(q, allowed)
            self.assertTrue(is_valid, f"HR question '{q}' rejected: {reason}")
            self.assertEqual(matched, TOPIC_HR_BEHAVIORAL)

        # Technical coding questions must be rejected
        self.assertFalse(validate_topic_question("Implement Dijkstra's shortest path algorithm", allowed)[0])
        self.assertFalse(validate_topic_question("Design a rate limiter for microservices", allowed)[0])

    # ------------------------------------------------------------------------
    # 5. MIXED TOPICS ROTATION
    # ------------------------------------------------------------------------
    def test_05_mixed_topics_rotation(self):
        allowed = [TOPIC_DSA, TOPIC_SYSTEM_DESIGN]
        questions = []
        for turn in range(2, 6):
            q = get_curated_fallback_question(turn, allowed, previous_questions=questions)
            questions.append(q)
            is_valid, matched, _ = validate_topic_question(q, allowed)
            self.assertTrue(is_valid, f"Question '{q}' not in mixed topics {allowed}")
            self.assertIn(matched, allowed)

        # HR question must still be rejected under mixed DSA + System Design
        self.assertFalse(validate_topic_question("Describe a difficult stakeholder you managed", allowed)[0])

    # ------------------------------------------------------------------------
    # 6. TOPIC VALIDATION & REJECTION GATES
    # ------------------------------------------------------------------------
    def test_06_topic_validation_rejection(self):
        # DSA track
        self.assertTrue(validate_topic_question("Explain binary search and its time complexity", [TOPIC_DSA])[0])
        self.assertTrue(validate_topic_question("Find the longest substring without repeating characters", [TOPIC_DSA])[0])
        self.assertFalse(validate_topic_question("Explain database normalization and 3NF", [TOPIC_DSA])[0])
        self.assertFalse(validate_topic_question("Design an e-commerce checkout system", [TOPIC_DSA])[0])

        # System Design track
        self.assertTrue(validate_topic_question("How would you design a distributed caching layer using Redis?", [TOPIC_SYSTEM_DESIGN])[0])
        self.assertFalse(validate_topic_question("How do you resolve interpersonal disagreements with peers?", [TOPIC_SYSTEM_DESIGN])[0])

    # ------------------------------------------------------------------------
    # 7. JOB DESCRIPTION MODE — PYTHON BACKEND
    # ------------------------------------------------------------------------
    def test_07_jd_mode_python_backend(self):
        role = "Python Backend Developer"
        jd = "Requirements: Python, Flask, REST APIs, PostgreSQL, Redis, Authentication"

        valid_q1 = "Explain how you would design a REST API using Flask."
        valid_q2 = "How would you implement JWT authentication in Python?"
        valid_q3 = "How would you optimize a PostgreSQL query for high read throughput?"
        invalid_q1 = "Explain convolutional neural networks and YOLO object detection."
        invalid_q2 = "Describe the React component lifecycle and virtual DOM diffing."

        self.assertTrue(validate_jd_question(valid_q1, role, jd)[0])
        self.assertTrue(validate_jd_question(valid_q2, role, jd)[0])
        self.assertTrue(validate_jd_question(valid_q3, role, jd)[0])
        self.assertFalse(validate_jd_question(invalid_q1, role, jd)[0])
        self.assertFalse(validate_jd_question(invalid_q2, role, jd)[0])

    # ------------------------------------------------------------------------
    # 8. JOB DESCRIPTION MODE — FRONTEND DEVELOPER
    # ------------------------------------------------------------------------
    def test_08_jd_mode_frontend(self):
        role = "Frontend React Developer"
        jd = "Requirements: React, TypeScript, Redux, CSS Modules, Browser Performance"

        valid_q = "How does React fiber architecture optimize component re-renders?"
        invalid_q = "Explain Linux kernel memory paging and page replacement algorithms."

        self.assertTrue(validate_jd_question(valid_q, role, jd)[0])
        self.assertFalse(validate_jd_question(invalid_q, role, jd)[0])

    # ------------------------------------------------------------------------
    # 9. JOB DESCRIPTION MODE — HR (STRICTLY NON-TECHNICAL)
    # ------------------------------------------------------------------------
    def test_09_jd_mode_hr_no_technical_questions(self):
        role = "HR Specialist / People Operations"
        jd = "Talent acquisition, recruitment pipelines, employee engagement, HR compliance, conflict resolution."

        valid_hr_q1 = "How do you handle a sensitive workplace conflict between two senior employees?"
        valid_hr_q2 = "What recruitment channels do you prioritize for niche candidate sourcing?"
        invalid_tech_q1 = "Explain binary search and implement it in Python."
        invalid_tech_q2 = "Design a scalable microservices architecture with Kafka."
        invalid_tech_q3 = "How do you optimize an SQL query with b-tree indexing?"

        self.assertTrue(validate_jd_question(valid_hr_q1, role, jd)[0])
        self.assertTrue(validate_jd_question(valid_hr_q2, role, jd)[0])

        # Mandatory constraint: HR must NEVER receive technical coding/architecture questions
        self.assertFalse(validate_jd_question(invalid_tech_q1, role, jd)[0])
        self.assertFalse(validate_jd_question(invalid_tech_q2, role, jd)[0])
        self.assertFalse(validate_jd_question(invalid_tech_q3, role, jd)[0])

        # Test curated question for HR
        fallback_q = get_curated_fallback_question(2, [TOPIC_HR_BEHAVIORAL], role=role, job_description=jd)
        self.assertTrue(validate_jd_question(fallback_q, role, jd)[0])
        self.assertNotIn("coding", fallback_q.lower())
        self.assertNotIn("sql", fallback_q.lower())

    # ------------------------------------------------------------------------
    # 10. OFF-TOPIC JD REJECTION
    # ------------------------------------------------------------------------
    def test_10_off_topic_jd_rejection(self):
        role = "Python Backend Developer"
        jd = "Python, Flask, PostgreSQL"
        is_valid, reason = validate_jd_question("Explain YOLO object detection with PyTorch", role, jd)
        self.assertFalse(is_valid)
        self.assertIn("rejected", reason.lower())

    # ------------------------------------------------------------------------
    # 11. SCORING — COMPLETELY CORRECT ANSWER
    # ------------------------------------------------------------------------
    def test_11_scoring_completely_correct_answer(self):
        q = "Explain binary search and its time complexity."
        ans = (
            "Binary search works on sorted arrays by repeatedly dividing the search space in halves. "
            "We compare the target with the middle element: if target is less, we search the left half; "
            "if greater, the right half. The time complexity is O(log N) because the search interval "
            "halves with each step, and space complexity is O(1) iteratively. The trade-off is that "
            "the input array must be sorted upfront."
        )
        classification, acc_score, dim_scores, _ = classify_candidate_response(q, ans, category=TOPIC_DSA)
        self.assertEqual(classification, CLASS_CORRECT_COMPLETE)
        self.assertGreaterEqual(acc_score, 75.0)

        # Verified strength extraction
        st = extract_verified_strength(classification, acc_score, q, ans, dim_scores)
        self.assertIsNotNone(st)
        self.assertIn("Algorithmic", st["competency"])

    # ------------------------------------------------------------------------
    # 12. SCORING — IRRELEVANT / OFF-TOPIC ANSWER
    # ------------------------------------------------------------------------
    def test_12_scoring_irrelevant_off_topic_answer(self):
        q = "Explain binary search and its time complexity."
        ans = "My favourite programming language is Python and I like pizza."

        eval_res = evaluate_response_comprehensive(
            resume_text="DSA Candidate",
            question=q,
            answer=ans,
            chat_model=None,
            question_index=2,
            category=TOPIC_DSA
        )
        self.assertEqual(eval_res["correctness"], CLASS_IRRELEVANT_OFF_TOPIC)
        self.assertLessEqual(eval_res["accuracy_score"], 20)
        self.assertLessEqual(eval_res["score"], 2.0)
        # CRITICAL: Zero false strengths
        self.assertEqual(eval_res["strength"], "")

    # ------------------------------------------------------------------------
    # 13. SCORING — NON-ANSWER ("I don't know", "skip", empty, "idk")
    # ------------------------------------------------------------------------
    def test_13_scoring_non_answer(self):
        q = "Explain how database indexing works."
        # Phase 6 Operating Rules R1 & R6: IntentClassifier-matched conversational/skip/noise
        # turns are NEVER scored (is_scored=False, score=None), while bare fallback no-answer ("idk")
        # returns deterministic 0.0 / 0 with zero fabricated strengths.
        unscored_intents = ["I don't know.", "skip", "", "no idea"]
        for non_ans in unscored_intents:
            eval_res = evaluate_response_comprehensive(
                resume_text="CS Candidate",
                question=q,
                answer=non_ans,
                chat_model=None,
                question_index=2,
                category=TOPIC_CS_FUNDAMENTALS
            )
            self.assertFalse(eval_res.get("is_scored", True))
            self.assertTrue(eval_res.get("is_conversational_turn"))
            self.assertIsNone(eval_res["accuracy_score"])
            self.assertIsNone(eval_res["score"])
            self.assertEqual(eval_res["strength"], "")

        bare_res = evaluate_response_comprehensive(
            resume_text="CS Candidate",
            question=q,
            answer="idk",
            chat_model=None,
            question_index=2,
            category=TOPIC_CS_FUNDAMENTALS
        )
        self.assertEqual(bare_res["accuracy_score"], 0)
        self.assertEqual(bare_res["score"], 0.0)
        self.assertEqual(bare_res["strength"], "")

    # ------------------------------------------------------------------------
    # 14. SCORING — EARLY EXIT ("can i end inw", "quit interview")
    # ------------------------------------------------------------------------
    def test_14_scoring_early_exit(self):
        q = "How would you shard a MySQL database?"
        # Operating Rules R1 & R6: explicit end_interview_request intents are treated as
        # unscored control turns (score=None, is_scored=False); direct fallback early-exit
        # strings without end intent return 0.0 / Early Exit with zero fabricated strengths.
        for exit_intent_ans in ["can i end inw", "i want to end"]:
            eval_res = evaluate_response_comprehensive(
                resume_text="Candidate",
                question=q,
                answer=exit_intent_ans,
                chat_model=None,
                question_index=3,
                category=TOPIC_SYSTEM_DESIGN
            )
            self.assertEqual(eval_res.get("intent"), "end_interview_request")
            self.assertFalse(eval_res.get("is_scored", True))
            self.assertIsNone(eval_res["accuracy_score"])
            self.assertIsNone(eval_res["score"])
            self.assertEqual(eval_res["strength"], "")

        for fallback_exit_ans in ["quit interview", "please end now"]:
            eval_res = evaluate_response_comprehensive(
                resume_text="Candidate",
                question=q,
                answer=fallback_exit_ans,
                chat_model=None,
                question_index=3,
                category=TOPIC_SYSTEM_DESIGN
            )
            self.assertEqual(eval_res["accuracy_score"], 0)
            self.assertEqual(eval_res["score"], 0.0)
            self.assertEqual(eval_res["strength"], "")
            self.assertIn("Early Exit", eval_res["answer_quality"])

    # ------------------------------------------------------------------------
    # 15. INCOMPLETE INTERVIEW REPORT PRORATION (< 5 valid answers)
    # ------------------------------------------------------------------------
    def test_15_incomplete_interview_report_proration(self):
        # Candidate answered only 1 question with 80% accuracy, then terminated
        report = fast_compile_report(
            role="Python Developer",
            track="Backend",
            difficulty="Medium",
            experience_level="1-3 Years",
            questions=["Explain REST APIs", "Explain caching", "Explain SQL"],
            responses=["REST APIs use HTTP methods like GET and POST for resource manipulation.", "can i end inw", ""],
            feedbacks=[
                {"accuracy_score": 80, "score": 8.0, "correctness": CLASS_CORRECT_COMPLETE, "strength": "REST API Architecture"},
                {"accuracy_score": 0, "score": 0.0, "correctness": CLASS_EARLY_EXIT, "strength": ""},
                {"accuracy_score": 0, "score": 0.0, "correctness": CLASS_NO_ANSWER, "strength": ""}
            ],
            interview_mode="job_description",
            candidate_name="Anushka"
        )

        # 1 valid response out of 10 total questions: score must be prorated by completion rate (1/10)
        # 80 * 0.1 = 8/100, NEVER 63 or 80!
        self.assertLessEqual(report["overall_score"], 15)
        self.assertEqual(report["grade"], "F")
        self.assertIn(report["report_type"], ["incomplete", "preliminary"])
        self.assertIn("Incomplete", report["recommendation"])

        # Top strengths fallback when insufficient evidence exists
        top_str = report.get("top_strengths", [])
        self.assertTrue(
            len(top_str) == 0 or "Insufficient evidence" in top_str[0] or len(report.get("strengths", [])) <= 1
        )

    # ------------------------------------------------------------------------
    # 16. EXECUTIVE SUMMARY DATA INTEGRITY & METADATA ISOLATION
    # ------------------------------------------------------------------------
    def test_16_executive_summary_data_integrity(self):
        report = fast_compile_report(
            role="HR Manager",
            track="HR & Behavioral",
            difficulty="Hard",
            experience_level="3-5 Years",
            questions=[
                "How do you resolve conflict?",
                "How do you structure compensation?",
                "What recruitment channels do you use?",
                "How do you handle underperformance?",
                "Describe an employee engagement initiative."
            ],
            responses=[
                "I use active listening, separate the individuals, identify root causes, and build mutually agreed action plans.",
                "I benchmark against market data using Radford surveys and balance base salary with performance incentives.",
                "I prioritize LinkedIn Recruiter, employee referrals, and specialized tech communities.",
                "I initiate a structured 30-day performance improvement plan with weekly measurable milestones.",
                "I launched a quarterly peer recognition program that boosted team engagement scores by 25%."
            ],
            feedbacks=[
                {"accuracy_score": 85, "score": 8.5, "correctness": CLASS_CORRECT_COMPLETE, "strength": "Conflict Resolution"},
                {"accuracy_score": 80, "score": 8.0, "correctness": CLASS_CORRECT_COMPLETE, "strength": "Compensation Design"},
                {"accuracy_score": 80, "score": 8.0, "correctness": CLASS_CORRECT_COMPLETE, "strength": "Sourcing Strategy"},
                {"accuracy_score": 75, "score": 7.5, "correctness": CLASS_PARTIALLY_CORRECT, "strength": "Performance Management"},
                {"accuracy_score": 85, "score": 8.5, "correctness": CLASS_CORRECT_COMPLETE, "strength": "Employee Engagement"}
            ],
            interview_mode="job_description",
            candidate_name="Anushka Saxena"
        )

        exec_sum = report.get("executive_summary", "")
        self.assertTrue(isinstance(exec_sum, dict))

        # 1. Candidate Name
        self.assertEqual(exec_sum.get("candidate_name"), "Anushka Saxena")
        # 2. Target Role
        self.assertEqual(exec_sum.get("target_role"), "HR Manager")
        self.assertNotIn("None", exec_sum.get("target_role"))
        self.assertNotIn("Software Engineer", exec_sum.get("target_role"))
        # 3. Interview Mode
        self.assertEqual(exec_sum.get("interview_mode"), "Job Description Mode")
        # 4. Selected Topics
        self.assertEqual(exec_sum.get("selected_topics"), "HR & Behavioral")
        # 5. Difficulty
        self.assertEqual(exec_sum.get("difficulty"), "Hard")
        self.assertNotIn("None difficulty", str(report))
        # 6. Questions attempted vs Total
        self.assertEqual(exec_sum.get("questions_attempted"), 5)
        self.assertGreaterEqual(exec_sum.get("total_questions"), 5)
        # 7. Valid answers
        self.assertEqual(exec_sum.get("valid_evaluated_answers"), 5)
        # 8. Score & Grade
        self.assertGreaterEqual(exec_sum.get("overall_score"), 75)
        self.assertIn(exec_sum.get("overall_grade"), ["A", "A-", "B+", "B"])
        # 9. Key strengths
        self.assertGreaterEqual(len(exec_sum.get("key_strengths", [])), 1)
        # 10. Evaluation summary narrative
        self.assertIn("HR Manager", report.get("report", ""))
        self.assertNotIn("None (None difficulty)", report.get("report", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
