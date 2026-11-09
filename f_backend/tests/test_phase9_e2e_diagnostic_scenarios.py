"""
Test Suite for Phase 9: End-to-End Diagnostic Scenarios & Staging Verification
Covers:
  - Profile A: Strong AI/ML Candidate (High proficiency, advanced adaptation, zero OS questions)
  - Profile B: Beginner AI/ML Candidate (Weak answers, prerequisite tracing, remedial assignments)
  - Profile C: SDE Candidate (DSA/System Design focus, isolation from AI/ML)
  - Security & Rate Limits: Daily 5-session limit, 10KB answer length bounds
"""

import unittest
import json
import uuid
import os
import sys
from datetime import datetime, timezone, timedelta

os.environ.setdefault("ENV", "test")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key-mock")
os.environ.setdefault("JWT_SECRET", "test-secret-key-12345678901234567890123456789012")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, _get_jwt_secret
import jwt
from local_supabase import SQLiteSupabaseMock
from services.adaptive_assessment_engine import AdaptiveAssessmentEngine
from services.weakness_detection_engine import WeaknessDetectionEngine


class TestPhase9E2EDiagnosticScenarios(unittest.TestCase):
    """End-to-End lifecycle tests verifying role isolation, adaptivity, and grounded weaknesses."""

    def setUp(self):
        self.client = SQLiteSupabaseMock(db_path=":memory:")

    def test_01_profile_a_strong_aiml_candidate(self):
        """Profile A: Strong AI/ML candidate gets ML questions, scores high, and triggers advanced adaptivity."""
        user_id = f"cand-strong-aiml-{uuid.uuid4().hex[:8]}"

        # Start AI/ML assessment
        session = AdaptiveAssessmentEngine.start_session(
            user_id=user_id,
            target_role="AI/ML Engineer",
            job_description="PyTorch, Transformer self-attention, diffusion models, and GPU acceleration.",
            experience_level="Junior",
            question_budget=3,
            supabase_client=self.client
        )
        ass_id = session["assessment_id"]
        q1 = session["current_question"]

        # Verify Q1 is AI/ML (never OS concurrency or general SDE)
        self.assertIn(q1["skill_id"], ["dl_transformers", "genai_llm_fundamentals", "ml_fundamentals", "math_linear_algebra", "math_probability_statistics"])
        self.assertNotIn("process and a thread", q1["question_text"].lower())

        # Answer Turn 1 matching domain of Question 1
        def get_best_answer(item):
            sid = item.get("skill_id", "")
            qtext = item.get("question_text", "").lower()
            if "eval" in sid or "imbalance" in qtext or "fraud" in qtext:
                return "Raw accuracy is misleading under 99.9% class imbalance because predicting all negative gives 99.9% accuracy. We prioritize Precision-Recall PR-AUC and F1-score. PR curves evaluate positive minority class precision vs recall whereas ROC curves get distorted by huge true negative counts."
            if "grad" in qtext or "resnet" in qtext or "neural" in sid:
                return "Vanishing gradients occur when backpropagating through deep layers where activation derivatives multiply repeatedly via chain rule. Residual skip connections mitigate this by providing an identity shortcut F(x) + x where d(F+x)/dx = dF/dx + 1, ensuring gradients flow back without vanishing."
            if "transformer" in sid or "attention" in qtext:
                return "Self-attention computes scaled dot-product attention softmax(QK^T / sqrt(d_k)) * V using Query, Key, and Value projection matrices. Large d_k pushes inner products into softmax vanishing gradient regions, so scaling preserves unit variance with O(N^2) pairwise attention time and space complexity."
            if "llm" in sid or "hallucinat" in qtext:
                return "Large language model hallucinations occur during next-token probability sampling without a grounded world model. Mitigation includes Retrieval-Augmented Generation (RAG) with vector databases, Chain-of-Thought reasoning self-consistency, and preference alignment via RLHF or DPO."
            if "sys_ml" in sid or "recommend" in qtext or "funnel" in qtext:
                return "Two-stage funnel: lightweight ANN vector retrieval to heavy cross-encoder ranking with sub-50ms latency SLA caching, and monitoring data drift covariate shift versus concept drift."
            return "Bayes theorem computes posterior probability P(A|B) = P(B|A) P(A) / P(B) where likelihood and prior distributions are normalized by marginal evidence. Maximum likelihood estimation maximizes log-likelihood over parameters."

        turn1_ans = get_best_answer(q1)
        res1 = AdaptiveAssessmentEngine.submit_turn(
            user_id=user_id,
            assessment_id=ass_id,
            turn_index=1,
            answer=turn1_ans,
            idempotency_key=f"{ass_id}_turn_1",
            supabase_client=self.client
        )
        self.assertEqual(res1["status"], "IN_PROGRESS")
        self.assertGreaterEqual(res1["evaluation"]["score"], 60.0)

        # Question 2 should remain within AI/ML domain
        q2 = res1["next_question"]
        self.assertTrue(any(prefix in q2["skill_id"] for prefix in ["dl_", "ml_", "genai_", "math_"]))

        # Answer Turn 2 matching question domain
        turn2_ans = get_best_answer(q2)
        res2 = AdaptiveAssessmentEngine.submit_turn(
            user_id=user_id,
            assessment_id=ass_id,
            turn_index=2,
            answer=turn2_ans,
            idempotency_key=f"{ass_id}_turn_2",
            supabase_client=self.client
        )
        self.assertEqual(res2["status"], "IN_PROGRESS")

        # Answer Turn 3 matching question domain
        q3 = res2["next_question"]
        turn3_ans = get_best_answer(q3)
        res3 = AdaptiveAssessmentEngine.submit_turn(
            user_id=user_id,
            assessment_id=ass_id,
            turn_index=3,
            answer=turn3_ans,
            idempotency_key=f"{ass_id}_turn_3",
            supabase_client=self.client
        )
        self.assertEqual(res3["status"], "COMPLETED")
        self.assertGreaterEqual(res3["overall_score"], 60.0)

    def test_02_profile_b_beginner_aiml_candidate_weaknesses(self):
        """Profile B: Beginner with low scores triggers grounded weaknesses and prerequisite gap detection."""
        user_id = f"cand-beginner-aiml-{uuid.uuid4().hex[:8]}"

        session = AdaptiveAssessmentEngine.start_session(
            user_id=user_id,
            target_role="AI/ML Engineer",
            job_description="Deep learning and machine learning algorithms.",
            question_budget=2,
            supabase_client=self.client
        )
        ass_id = session["assessment_id"]

        # Submit evasive/weak answer for Turn 1
        res1 = AdaptiveAssessmentEngine.submit_turn(
            user_id=user_id,
            assessment_id=ass_id,
            turn_index=1,
            answer="I am not sure about the mathematical formula, I usually just import the library.",
            idempotency_key=f"{ass_id}_turn_1",
            supabase_client=self.client
        )
        self.assertLess(res1["evaluation"]["score"], 50.0)

        # Submit weak answer for Turn 2
        res2 = AdaptiveAssessmentEngine.submit_turn(
            user_id=user_id,
            assessment_id=ass_id,
            turn_index=2,
            answer="I don't know.",
            idempotency_key=f"{ass_id}_turn_2",
            supabase_client=self.client
        )
        self.assertEqual(res2["status"], "COMPLETED")

        # Verify Grounded Weakness Engine detects failure
        weakness_data = WeaknessDetectionEngine.detect_weaknesses_and_uncertainties(
            user_id=user_id,
            target_role="ai_ml_engineer",
            supabase_client=self.client
        )
        failures = weakness_data["verified_weaknesses"]
        self.assertGreaterEqual(len(failures), 1)
        self.assertIn("remedial_action", failures[0])

    def test_03_profile_c_sde_candidate_isolation(self):
        """Profile C: SDE candidate receives DSA/System Design questions, isolated from AI/ML."""
        user_id = f"cand-sde-{uuid.uuid4().hex[:8]}"

        session = AdaptiveAssessmentEngine.start_session(
            user_id=user_id,
            target_role="Software Engineer (SDE / SWE)",
            job_description="Data Structures, Algorithms, Distributed Systems, and Low-latency Architecture.",
            question_budget=2,
            supabase_client=self.client
        )
        ass_id = session["assessment_id"]
        q1 = session["current_question"]

        # Must be DSA or System Design
        self.assertTrue(q1["skill_id"].startswith("dsa_") or q1["skill_id"].startswith("sys_") or q1["skill_id"].startswith("cs_"))
        self.assertFalse(q1["skill_id"].startswith("dl_"))
        self.assertFalse(q1["skill_id"].startswith("genai_"))

    def test_04_daily_session_limit_and_response_bounds(self):
        """Verifies max 5 sessions per 24 hours per user and rejects payloads > 10KB."""
        user_id = f"cand-limit-{uuid.uuid4().hex[:8]}"

        # Start 5 sessions successfully
        for i in range(5):
            AdaptiveAssessmentEngine.start_session(
                user_id=user_id,
                target_role="Software Engineer (SDE / SWE)",
                supabase_client=self.client
            )

        # 6th session must fail with quota error
        with self.assertRaises(ValueError) as ctx:
            AdaptiveAssessmentEngine.start_session(
                user_id=user_id,
                target_role="Software Engineer (SDE / SWE)",
                supabase_client=self.client
            )
        self.assertIn("limit reached", str(ctx.exception).lower())

        # Test response size bound > 10,000 characters
        cand_user = f"cand-size-{uuid.uuid4().hex[:8]}"
        sess = AdaptiveAssessmentEngine.start_session(
            user_id=cand_user,
            target_role="Software Engineer (SDE / SWE)",
            supabase_client=self.client
        )
        huge_answer = "A" * 10500
        with self.assertRaises(ValueError) as ctx:
            AdaptiveAssessmentEngine.submit_turn(
                user_id=cand_user,
                assessment_id=sess["assessment_id"],
                turn_index=1,
                answer=huge_answer,
                idempotency_key="too_big",
                supabase_client=self.client
            )
        self.assertIn("10,000 characters", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
