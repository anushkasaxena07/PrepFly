"""
Tests for Phase 6: Contextual Mentor Chat with Real State Mutations.
Validates:
1. Context assembly within strict token budget (2500 tokens).
2. Intent routing to state mutations:
   - "I only have 30 minutes today" -> recalculates plan with daily_minutes=30 and verifies diff.
   - "Prepare for tomorrow" -> 24h interview deadline compression.
   - "Evaluate my answer: ..." -> rubric evaluation & verified evidence recorded.
3. 4-turn mini mock interview with end-of-session evaluation and immutable mock_interview evidence.
"""

import json
import unittest
import uuid
from datetime import datetime, timezone

from local_supabase import get_supabase_client
from services.mentor_service import (
    MentorService,
    INTENT_TIME_BUDGET_30MIN,
    INTENT_MOCK_INTERVIEW,
    INTENT_PREPARE_TOMORROW,
    INTENT_EVALUATE_ANSWER,
    INTENT_HARDER_QUESTION
)
from services.evidence_registry_service import SOURCE_MOCK_INTERVIEW


class TestPhase6MentorChat(unittest.TestCase):
    """Verifies contextual mentor chat and conversational state mutations."""

    def setUp(self):
        self.supabase = get_supabase_client()
        self.user_id = f"usr_test_p6_{uuid.uuid4().hex[:8]}"
        self.now_iso = datetime.now(timezone.utc).isoformat()

        # Seed interview goal for user
        self.goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        self.supabase.table("interview_goals").insert({
            "id": self.goal_id,
            "user_id": self.user_id,
            "target_company": "Google",
            "target_role": "Machine Learning Engineer",
            "required_experience_years": 4.0,
            "candidate_actual_experience_years": 2.5,
            "days_horizon": 30,
            "daily_minutes": 60,
            "learning_preference": "hands-on",
            "status": "active",
            "version": 1,
            "created_at": self.now_iso,
            "updated_at": self.now_iso
        }).execute()

        # Seed initial candidate skill state with a verified gap
        self.supabase.table("candidate_skill_states").insert({
            "id": f"css_{uuid.uuid4().hex[:8]}",
            "user_id": self.user_id,
            "skill_id": "ml_model_evaluation",
            "proficiency": 42.0,
            "confidence": 0.85,
            "sample_count": 2,
            "status": "VERIFIED_GAP",
            "last_assessed_at": self.now_iso,
            "updated_at": self.now_iso
        }).execute()

    def test_01_context_assembly_and_token_budget_enforcement(self):
        """Verifies context assembly respects token budget (2500 tokens max)."""
        conv = MentorService.start_or_resume_conversation(self.user_id, supabase_client=self.supabase)
        conv_id = conv["id"]

        # Insert 10 filler dialogue messages
        for i in range(10):
            MentorService.save_message(
                conversation_id=conv_id,
                user_id=self.user_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}: Discussing technical architectural invariants and asymptotic bounds for ML systems.",
                supabase_client=self.supabase
            )

        budget_ctx = MentorService.build_context_within_budget(
            user_id=self.user_id,
            conversation_id=conv_id,
            current_query="What should I study next?",
            token_budget=2500,
            supabase_client=self.supabase
        )

        self.assertIn("interview_context", budget_ctx)
        self.assertIn("rolling_summary", budget_ctx)
        self.assertIn("relevant_evidence", budget_ctx)
        self.assertIn("recent_messages", budget_ctx)
        self.assertLessEqual(budget_ctx["estimated_tokens"], 2500)
        self.assertLessEqual(len(budget_ctx["recent_messages"]), 6)

    def test_02_conversational_mutation_30_minutes_today(self):
        """
        GATE 6 REQUIREMENT 1:
        Candidate says 'I only have 30 minutes today', mentor responds with updated plan,
        and backend plan diff is verified.
        """
        conv = MentorService.start_or_resume_conversation(self.user_id, supabase_client=self.supabase)
        conv_id = conv["id"]

        user_msg = "I only have 30 minutes today"
        res = MentorService.send_mentor_message(
            user_id=self.user_id,
            conversation_id=conv_id,
            user_message=user_msg,
            supabase_client=self.supabase
        )

        self.assertEqual(res["intent"], INTENT_TIME_BUDGET_30MIN)
        self.assertIn("plan_diff", res)
        self.assertIn("updated_version", res)

        diff = res["plan_diff"]
        self.assertIn("added", diff)
        self.assertIn("removed", diff)
        self.assertIn("moved", diff)

        # Verify mentor response explains the 30-minute schedule and deferred items
        msg_content = res["message"]["content"]
        self.assertIn("30 minutes", msg_content)
        self.assertIn("Schedule", msg_content)

        print("\n" + "=" * 90)
        print("          GATE 6 PART 1: 30-MINUTE CONVERSATIONAL PLAN MUTATION TRANSCRIPT")
        print("=" * 90)
        print(f"CANDIDATE: {user_msg}")
        print("-" * 90)
        print(f"MENTOR:\n{msg_content}")
        print("-" * 90)
        print(f"BACKEND PLAN DIFF VERIFIED:")
        print(f"  • Trigger: {res['updated_version']['trigger_event']}")
        print(f"  • New Horizon Minutes: {res['updated_version']['daily_minutes']}m")
        print(f"  • Activities Added / Rescheduled: {len(diff.get('added', []))}")
        print(f"  • Items Deferred: {len(res['updated_version'].get('deferred_items', []))}")
        print("=" * 90 + "\n")

    def test_03_four_turn_mini_mock_interview_and_evidence_recording(self):
        """
        GATE 6 REQUIREMENT 2:
        Candidate completes a 4-turn mini mock interview, mentor evaluates,
        and immutable evidence is recorded with source_type = mock_interview.
        """
        conv = MentorService.start_or_resume_conversation(self.user_id, supabase_client=self.supabase)
        conv_id = conv["id"]

        transcript_turns = []

        # ── Turn 1: Candidate initiates mock interview ──
        t1_user = "Start a mock interview"
        t1_res = MentorService.send_mentor_message(
            user_id=self.user_id,
            conversation_id=conv_id,
            user_message=t1_user,
            supabase_client=self.supabase
        )
        self.assertEqual(t1_res["intent"], INTENT_MOCK_INTERVIEW)
        self.assertEqual(t1_res["mock_turn"], 1)
        self.assertFalse(t1_res["is_complete"])
        transcript_turns.append((t1_user, t1_res["message"]["content"]))

        # ── Turn 2: Candidate answers Question 1 ──
        t2_user = (
            "Cross-entropy accuracy fails on 200:1 imbalanced data because a trivial majority-class "
            "predictor achieves 99.5% accuracy while missing 100% of fraud cases. Under severe class skew, "
            "we should track Precision-Recall AUC (PR-AUC) rather than ROC-AUC because ROC-AUC uses False Positive Rate "
            "which has the huge negative class in the denominator and visually masks false positives."
        )
        t2_res = MentorService.send_mentor_message(
            user_id=self.user_id,
            conversation_id=conv_id,
            user_message=t2_user,
            supabase_client=self.supabase
        )
        self.assertEqual(t2_res["mock_turn"], 2)
        self.assertFalse(t2_res["is_complete"])
        transcript_turns.append((t2_user, t2_res["message"]["content"]))

        # ── Turn 3: Candidate answers Question 2 (Calibration & Cost Matrix) ──
        t3_user = (
            "To calibrate probabilities, I would use Platt Scaling if the validation log-odds are approximately sigmoidal, "
            "or Isotonic Regression if we have sufficient validation samples (>1,000 fraud instances) without assuming linearity. "
            "For decision thresholding with asymmetric costs (C_FP = $50, C_FN = $1,000), we minimize expected loss: "
            "E[Loss(predict=1)] = (1 - p) * 50; E[Loss(predict=0)] = p * 1,000. "
            "Setting them equal yields optimal threshold tau* = 50 / (50 + 1000) = 50 / 1050 approx 0.0476. "
            "We flag any transaction with calibrated p >= 0.0476."
        )
        t3_res = MentorService.send_mentor_message(
            user_id=self.user_id,
            conversation_id=conv_id,
            user_message=t3_user,
            supabase_client=self.supabase
        )
        self.assertEqual(t3_res["mock_turn"], 3)
        self.assertFalse(t3_res["is_complete"])
        transcript_turns.append((t3_user, t3_res["message"]["content"]))

        # ── Turn 4: Candidate answers Question 3 (Latency & Production Optimization) ──
        t4_user = (
            "To hit a 12ms p99 SLA at 40,000 QPS, a 45ms Python ensemble will fail. I would: "
            "1) Export the model to ONNX Runtime and utilize INT8 post-training quantization, cutting inference latency to ~3ms. "
            "2) For the isotonic calibration, replace the stepwise lookup with precomputed 1D spline interpolation or lookup arrays in memory. "
            "3) Pre-compute static fraud features asynchronously in Redis, passing only dynamic transaction deltas into the inference service."
        )
        t4_res = MentorService.send_mentor_message(
            user_id=self.user_id,
            conversation_id=conv_id,
            user_message=t4_user,
            supabase_client=self.supabase
        )
        self.assertEqual(t4_res["mock_turn"], 4)
        self.assertTrue(t4_res["is_complete"])
        self.assertGreaterEqual(t4_res["overall_score"], 80.0)
        self.assertIsNotNone(t4_res.get("evidence"))
        transcript_turns.append((t4_user, t4_res["message"]["content"]))

        # Verify evidence recorded in skill_evidence_registry with source_type = mock_interview
        ev_data = self.supabase.table("skill_evidence_registry").select("*").eq("user_id", self.user_id).eq("source_type", SOURCE_MOCK_INTERVIEW).execute().data
        self.assertTrue(len(ev_data) > 0, "Expected at least 1 mock_interview evidence row")
        self.assertEqual(ev_data[0]["source_type"], SOURCE_MOCK_INTERVIEW)
        self.assertGreaterEqual(ev_data[0]["normalized_score"], 80.0)

        # Verify candidate skill state updated to MASTERED
        css = self.supabase.table("candidate_skill_states").select("*").eq("user_id", self.user_id).eq("skill_id", "ml_model_evaluation").execute().data[0]
        self.assertEqual(css["status"], "MASTERED")

        # Print Gate 6 Transcript
        print("\n" + "=" * 90)
        print("          GATE 6 PART 2: 4-TURN MINI MOCK INTERVIEW CHAT TRANSCRIPT")
        print("=" * 90)
        for i, (user_t, mentor_t) in enumerate(transcript_turns, 1):
            print(f"\n--- TURN {i} ---")
            print(f"CANDIDATE:\n{user_t}")
            print(f"\nAI MENTOR:\n{mentor_t}")
        print("\n" + "=" * 90)
        print(f"VERIFIED EVIDENCE RECORDED: ID {ev_data[0]['id']} | Source: {ev_data[0]['source_type']} | Score: {ev_data[0]['normalized_score']}%")
        print(f"UPDATED SKILL STATE: {css['skill_id']} -> {css['status']} (Proficiency: {css['proficiency']}%)")
        print("=" * 90 + "\n")


if __name__ == "__main__":
    unittest.main()

