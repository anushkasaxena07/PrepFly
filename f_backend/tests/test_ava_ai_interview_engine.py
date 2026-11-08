"""
Comprehensive Automated Test Suite for PrepFly Ava AI Interview Engine
Validates:
1. Interview State Machine & Transition Invariants
2. Idempotency Key & Turn Audit Ledger
3. Conversational Intent Detection (Repeat, Clarify, Pause, Early Exit)
4. Interviewer Personalities & Consistent Scoring Invariant
5. Resume Claim Extraction, Provenance & Anti-Hallucination Guard
6. Deterministic Adaptive Policies (Follow-up, Increase Difficulty, Simplify)
7. Session Knowledge Map Lifecycle
8. Typed Rubric Evaluation (Technical, System Design, Behavioral/STAR, Coding)
9. Question Bank Retrieval & Anti-Repetition Filtering
10. Session Recovery After Disconnect
11. Modern REST API Endpoints (/api/interview/*)
"""

import unittest
import json
import uuid
import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from local_supabase import SQLiteSupabaseMock
from services.interview_state_service import (
    InterviewStateService,
    STATE_INITIALIZING,
    STATE_ASKING,
    STATE_WAITING_FOR_RESPONSE,
    STATE_ANALYZING,
    STATE_FOLLOW_UP,
    STATE_CLARIFICATION,
    STATE_NEXT_QUESTION,
    STATE_PAUSED,
    STATE_COMPLETED,
    STATE_FAILED
)
from services.interviewer_personality_service import (
    InterviewerPersonalityService,
    PERSONALITY_FRIENDLY,
    PERSONALITY_PROFESSIONAL,
    PERSONALITY_CHALLENGING,
    PERSONALITY_STRICT,
    PERSONALITY_SENIOR_ENGINEER
)
from services.resume_intelligence_service import ResumeIntelligenceService
from services.answer_analyzer import (
    AnswerAnalyzer,
    INTENT_REPEAT,
    INTENT_CLARIFY,
    INTENT_PAUSE,
    INTENT_NO_ANSWER,
    INTENT_CORRECTION,
    INTENT_EARLY_EXIT,
    INTENT_ANSWER
)
from services.adaptive_interview_engine import (
    AdaptiveInterviewEngine,
    DECISION_FOLLOW_UP,
    DECISION_INCREASE_DIFFICULTY,
    DECISION_SIMPLIFY,
    DECISION_CLARIFY,
    DECISION_CHANGE_TOPIC,
    DECISION_END_INTERVIEW
)
from services.evaluation_service import (
    EvaluationService,
    INTERVIEW_TYPE_TECHNICAL,
    INTERVIEW_TYPE_SYSTEM_DESIGN,
    INTERVIEW_TYPE_BEHAVIORAL,
    INTERVIEW_TYPE_CODING
)
from services.question_bank_service import QuestionBankService
from app import app


class TestAvaAiInterviewEngine(unittest.TestCase):

    def setUp(self):
        self.supabase = SQLiteSupabaseMock()
        self.session_id = f"sess_{uuid.uuid4().hex[:10]}"
        self.user_id = f"user_{uuid.uuid4().hex[:8]}"

        # Initialize mock session
        self.supabase.table("sessions").insert({
            "session_id": self.session_id,
            "user_id": self.user_id,
            "category": "DSA",
            "role": "Backend Engineer",
            "difficulty": "Medium",
            "personality": "professional",
            "interview_state": STATE_INITIALIZING,
            "question_index": 1,
            "turn_count": 0,
            "questions": json.dumps(["How does stack and heap memory differ in Python?"]),
            "responses": json.dumps([]),
            "feedbacks": json.dumps([]),
            "scores": json.dumps([]),
            "knowledge_map": "{}",
            "active": True
        }).execute()

        self.client = app.test_client()
        self.client.testing = True

    # ------------------------------------------------------------------------
    # 1. State Machine & Transitions
    # ------------------------------------------------------------------------
    def test_01_state_machine_transitions(self):
        # Valid forward transitions
        self.assertTrue(InterviewStateService.validate_transition(STATE_INITIALIZING, STATE_ASKING))
        self.assertTrue(InterviewStateService.validate_transition(STATE_ASKING, STATE_WAITING_FOR_RESPONSE))
        self.assertTrue(InterviewStateService.validate_transition(STATE_WAITING_FOR_RESPONSE, STATE_ANALYZING))
        self.assertTrue(InterviewStateService.validate_transition(STATE_ANALYZING, STATE_FOLLOW_UP))
        self.assertTrue(InterviewStateService.validate_transition(STATE_FOLLOW_UP, STATE_WAITING_FOR_RESPONSE))
        self.assertTrue(InterviewStateService.validate_transition(STATE_WAITING_FOR_RESPONSE, STATE_COMPLETED))

        # Invalid transitions
        self.assertFalse(InterviewStateService.validate_transition(STATE_COMPLETED, STATE_ASKING))
        self.assertFalse(InterviewStateService.validate_transition(STATE_INITIALIZING, STATE_COMPLETED))
        self.assertFalse(InterviewStateService.validate_transition("UNKNOWN_STATE", STATE_ASKING))

        # Test state transition execution on DB
        success = InterviewStateService.transition_state(self.supabase, self.session_id, STATE_ASKING)
        self.assertTrue(success)
        state = InterviewStateService.get_session_state(self.supabase, self.session_id)
        self.assertEqual(state["interview_state"], STATE_ASKING)

    # ------------------------------------------------------------------------
    # 2. Idempotency & Turn Audit Recording
    # ------------------------------------------------------------------------
    def test_02_idempotency_and_turn_recording(self):
        request_id = f"req_{uuid.uuid4().hex[:8]}"

        # Record a turn
        eval_data = {
            "accuracy_score": 85,
            "overall_score": 8.5,
            "classification": "Correct and complete",
            "question_type": "Technical"
        }
        turn_recorded = InterviewStateService.record_turn(
            supabase_client=self.supabase,
            session_id=self.session_id,
            turn_number=1,
            question_text="How does stack and heap memory differ in Python?",
            candidate_response="Stack is for local frame references and function calls; heap dynamically allocates objects.",
            intent="ANSWER",
            decision="INCREASE_DIFFICULTY",
            score=8.5,
            accuracy_score=85,
            evaluation=eval_data,
            stage="Phase 4: Core Technical Discussion",
            request_id=request_id
        )
        self.assertTrue(turn_recorded)

        # Idempotency check: same request_id must return cached result
        cached = InterviewStateService.check_idempotency(self.supabase, self.session_id, request_id)
        self.assertIsNotNone(cached)
        self.assertTrue(cached["is_cached"])
        self.assertEqual(cached["turn_number"], 1)
        self.assertEqual(cached["score"], 8.5)

        # Non-existent request_id returns None
        self.assertIsNone(InterviewStateService.check_idempotency(self.supabase, self.session_id, "unknown_req"))

    # ------------------------------------------------------------------------
    # 3. Conversational Intent Detection
    # ------------------------------------------------------------------------
    def test_03_conversational_intent_detection(self):
        self.assertEqual(AnswerAnalyzer.detect_conversational_intent("Can you repeat the question please?"), INTENT_REPEAT)
        self.assertEqual(AnswerAnalyzer.detect_conversational_intent("Pardon?"), INTENT_REPEAT)
        self.assertEqual(AnswerAnalyzer.detect_conversational_intent("What do you mean by that?"), INTENT_CLARIFY)
        self.assertEqual(AnswerAnalyzer.detect_conversational_intent("Let me think for a second."), INTENT_PAUSE)
        self.assertEqual(AnswerAnalyzer.detect_conversational_intent("I don't know the answer to this."), INTENT_NO_ANSWER)
        self.assertEqual(AnswerAnalyzer.detect_conversational_intent("Actually wait, let me correct what I just said."), INTENT_CORRECTION)
        self.assertEqual(AnswerAnalyzer.detect_conversational_intent("Can I end the interview early?"), INTENT_EARLY_EXIT)

        # Substantive technical answers must be detected as INTENT_ANSWER
        tech_ans = "In Python, memory is managed via private heap space with reference counting and a generational cyclic garbage collector."
        self.assertEqual(AnswerAnalyzer.detect_conversational_intent(tech_ans), INTENT_ANSWER)

        # Check conversational response generator
        repeat_resp = AnswerAnalyzer.generate_conversational_response_for_intent(INTENT_REPEAT, "What is a deadlock?")
        self.assertIn("repeat", repeat_resp["message"].lower())
        self.assertFalse(repeat_resp["done"])

    # ------------------------------------------------------------------------
    # 4. Interviewer Personalities
    # ------------------------------------------------------------------------
    def test_04_interviewer_personalities(self):
        personalities = InterviewerPersonalityService.get_supported_personalities()
        expected = [
            PERSONALITY_FRIENDLY,
            PERSONALITY_PROFESSIONAL,
            PERSONALITY_CHALLENGING,
            PERSONALITY_STRICT,
            PERSONALITY_SENIOR_ENGINEER
        ]
        for p in expected:
            self.assertIn(p, personalities)
            profile = InterviewerPersonalityService.resolve_personality(p)
            self.assertIn("prompt_directives", profile)
            self.assertTrue(len(profile["acknowledgments"]) > 0)

            # Check prompt modifier includes the critical objective evaluation invariant
            modifier = InterviewerPersonalityService.get_prompt_modifier(p)
            self.assertIn("CRITICAL EVALUATION INVARIANT", modifier)
            self.assertIn("Rubric standards remain identical", modifier)

        # Unknown personality defaults to professional
        fallback = InterviewerPersonalityService.resolve_personality("unknown_personality")
        self.assertEqual(fallback["id"], PERSONALITY_PROFESSIONAL)

    # ------------------------------------------------------------------------
    # 5. Resume Extraction, Provenance & Anti-Hallucination Guard
    # ------------------------------------------------------------------------
    def test_05_resume_intelligence_and_anti_hallucination(self):
        raw_resume = """
        John Doe
        Email: john@example.com
        SKILLS:
        Languages: Python, TypeScript, SQL
        Frameworks: FastAPI, React, Docker, Redis
        PROJECTS:
        Distributed Rate Limiter | Python, Redis, FastAPI
        Implemented sliding window rate limiting algorithm capable of handling 50k requests/sec.
        E-Commerce Order Service | TypeScript, PostgreSQL
        Architected asynchronous order processing pipeline using RabbitMQ.
        EXPERIENCE:
        Software Engineer at CloudTech (2 years experience)
        """
        profile = ResumeIntelligenceService.extract_structured_candidate_profile(raw_resume)
        self.assertIn("Python", profile["languages"])
        self.assertIn("TypeScript", profile["languages"])
        self.assertIn("Redis", profile["databases"])
        self.assertIn("Docker", profile["tools"])
        self.assertTrue(len(profile["projects"]) >= 2)
        self.assertEqual(profile["experience_years_estimated"], 2.0)
        self.assertTrue(len(profile["verified_claims"]) >= 5)

        # Anti-hallucination check: grounded question passes
        grounded_q = "In your Distributed Rate Limiter project using Redis, how did you handle atomic counter increments?"
        is_clean, _ = ResumeIntelligenceService.detect_question_hallucination(grounded_q, profile)
        self.assertTrue(is_clean)

        # Ungrounded question asserting unverified tech (e.g., YOLOv8, Angular) fails
        hallucinated_q = "In your project using YOLO and Angular, how did you optimize inference latency?"
        is_clean_h, reason = ResumeIntelligenceService.detect_question_hallucination(hallucinated_q, profile)
        self.assertFalse(is_clean_h)
        self.assertIn("not in verified claims", reason)

    # ------------------------------------------------------------------------
    # 6. Deterministic Adaptive Policies
    # ------------------------------------------------------------------------
    def test_06_deterministic_adaptive_decisions(self):
        # 1. High score (>=85) with clean concepts -> INCREASE_DIFFICULTY
        action_high = AdaptiveInterviewEngine.evaluate_next_action(
            accuracy_score=90,
            concept_analysis={"missing_concepts": [], "word_count": 40},
            turn_number=2
        )
        self.assertEqual(action_high, DECISION_INCREASE_DIFFICULTY)

        # 2. Good score (65-84) with partial understanding -> FOLLOW_UP
        action_followup = AdaptiveInterviewEngine.evaluate_next_action(
            accuracy_score=75,
            concept_analysis={"partially_understood_concepts": ["garbage_collection"], "word_count": 30},
            turn_number=3
        )
        self.assertEqual(action_followup, DECISION_FOLLOW_UP)

        # 3. Repeated struggle (<40 score) -> SIMPLIFY
        action_simplify = AdaptiveInterviewEngine.evaluate_next_action(
            accuracy_score=25,
            concept_analysis={"missing_concepts": ["core_concept"], "word_count": 10},
            turn_number=3,
            consecutive_struggles=1
        )
        self.assertEqual(action_simplify, DECISION_SIMPLIFY)

        # 4. Turn 10 reached -> END_INTERVIEW
        action_end = AdaptiveInterviewEngine.evaluate_next_action(
            accuracy_score=80,
            concept_analysis={},
            turn_number=10
        )
        self.assertEqual(action_end, DECISION_END_INTERVIEW)

    # ------------------------------------------------------------------------
    # 7. Session Knowledge Map Lifecycle
    # ------------------------------------------------------------------------
    def test_07_session_knowledge_map(self):
        initial_map = {}
        concept_data = {
            "demonstrated_concepts": ["stack_memory", "heap_memory"],
            "partially_understood_concepts": ["reference_counting"],
            "missed_concepts": ["cyclic_garbage_collector"],
            "misconceptions": []
        }
        updated = AdaptiveInterviewEngine.update_session_knowledge_map(
            initial_map,
            topic="Python",
            subtopic="Memory Management",
            concept_analysis=concept_data,
            accuracy_score=75
        )
        entry = updated["python"]["memory_management"]
        self.assertEqual(entry["proficiency_evidence"], "strong")
        self.assertEqual(entry["concepts"]["stack_memory"], "demonstrated")
        self.assertEqual(entry["concepts"]["heap_memory"], "demonstrated")
        self.assertEqual(entry["concepts"]["reference_counting"], "partial")
        self.assertEqual(entry["concepts"]["cyclic_garbage_collector"], "unverified")

    # ------------------------------------------------------------------------
    # 8. Typed Rubric Evaluation
    # ------------------------------------------------------------------------
    def test_08_typed_rubric_evaluators(self):
        # Technical evaluation
        tech_eval = EvaluationService.evaluate_response_with_rubric(
            interview_type=INTERVIEW_TYPE_TECHNICAL,
            question="What is the difference between a process and a thread?",
            answer="A process has an independent memory space, while threads share heap and static data with separate stacks.",
            chat_model=None,
            role="Backend Engineer"
        )
        self.assertIn("accuracy_score", tech_eval)
        self.assertIn("criteria", tech_eval)
        self.assertTrue(len(tech_eval["criteria"]) >= 2)

        # Coding evaluation with authoritative sandbox metrics
        code_metrics = {
            "passed": 5,
            "total": 5,
            "time_complexity": "O(N)",
            "space_complexity": "O(1)",
            "runtime_error": None
        }
        code_eval = EvaluationService.evaluate_response_with_rubric(
            interview_type=INTERVIEW_TYPE_CODING,
            question="Reverse a linked list in O(1) space",
            answer="def reverse(head): ...",
            chat_model=None,
            coding_execution_metrics=code_metrics
        )
        self.assertEqual(code_eval["accuracy_score"], 90)
        self.assertEqual(code_eval["evaluation_confidence"], "authoritative_execution")

        # Empty answer returns deterministic 0-score
        empty_eval = EvaluationService.evaluate_response_with_rubric(
            interview_type=INTERVIEW_TYPE_TECHNICAL,
            question="Explain CAP theorem",
            answer="",
            chat_model=None
        )
        self.assertEqual(empty_eval["accuracy_score"], 0)
        self.assertEqual(empty_eval["classification"], "No Answer")

    # ------------------------------------------------------------------------
    # 9. Question Bank Retrieval & Anti-Repetition
    # ------------------------------------------------------------------------
    def test_09_question_bank_retrieval(self):
        q = QuestionBankService.select_best_question(
            topic="DSA",
            difficulty="Medium",
            previous_question_texts=[]
        )
        self.assertIsNotNone(q)
        self.assertEqual(q["topic"], "DSA")
        self.assertIn("expected_concepts", q)
        self.assertIn("rubric", q)

        # Exclude already asked question
        q2 = QuestionBankService.select_best_question(
            topic="DSA",
            difficulty="Medium",
            previous_question_texts=[q["question_text"]]
        )
        self.assertNotEqual(q["question_text"], q2["question_text"])

    # ------------------------------------------------------------------------
    # 10. Session Recovery After Disconnect
    # ------------------------------------------------------------------------
    def test_10_session_recovery(self):
        recovery = InterviewStateService.recover_session(self.supabase, self.session_id)
        self.assertTrue(recovery["recovered"])
        self.assertEqual(recovery["session_id"], self.session_id)
        self.assertEqual(recovery["personality"], "professional")
        self.assertIn("How does stack and heap", recovery["current_question"])

    # ------------------------------------------------------------------------
    # 11. REST API Endpoints (/api/interview/*)
    # ------------------------------------------------------------------------
    def test_11_rest_api_interview_routes(self):
        # 1. Personalities endpoint
        p_res = self.client.get("/api/interview/personalities")
        self.assertEqual(p_res.status_code, 200)
        p_data = p_res.get_json()
        self.assertEqual(p_data["status"], "success")
        self.assertEqual(len(p_data["personalities"]), 5)

        # 2. Session Recovery endpoint
        r_res = self.client.get(f"/api/interview/session/{self.session_id}/recover")
        self.assertEqual(r_res.status_code, 200)
        r_data = r_res.get_json()
        self.assertTrue(r_data["session"]["recovered"])

        # 3. Pause & Resume endpoints
        pause_res = self.client.post(f"/api/interview/session/{self.session_id}/pause")
        self.assertEqual(pause_res.status_code, 200)
        self.assertEqual(pause_res.get_json()["interview_state"], STATE_PAUSED)

        resume_res = self.client.post(f"/api/interview/session/{self.session_id}/resume")
        self.assertEqual(resume_res.status_code, 200)
        self.assertEqual(resume_res.get_json()["interview_state"], STATE_WAITING_FOR_RESPONSE)

        # 4. Resume profile extraction endpoint
        prof_res = self.client.post("/api/interview/resume/profile", json={
            "resume_text": "Skills: Python, Django, PostgreSQL, Docker. Project: Microservices Auth API."
        })
        self.assertEqual(prof_res.status_code, 200)
        prof_data = prof_res.get_json()
        self.assertIn("Python", prof_data["profile"]["skills"])


if __name__ == "__main__":
    unittest.main()

