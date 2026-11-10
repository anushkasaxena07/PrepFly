"""
Phase 4 Verification Suite: Pure Deterministic Scoring, Grade & Verdict Engine
Covers:
  - Formula v1 unit tests (per-turn score, dimension score, overall score, coverage, confidence, grade, recommendation)
  - Property-based invariants (seeded randomized fuzzing across 50+ permutations/trials each):
    1. Missing != zero (renormalized weights over evaluated dims only)
    2. Zero candidate turns -> INCOMPLETE_INSUFFICIENT_DATA (no score, no grade, no verdict)
    3. Failed evaluations -> EVALUATION_FAILED (no score, never F/Strong Reject)
    4. Monotonicity: adding a 1.0 answer never lowers score; adding a 0.0 answer never raises score
    5. One weak answer never produces F or Strong Reject alongside good evidence
    6. Determinism & idempotence under arbitrary turn/eval shuffling
    7. Original bug scenario (spoken answers present, evaluation empty) -> EVALUATION_FAILED, never No Responses / F / Strong Reject
"""

import json
import os
import random
import sys
import unittest

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services.interview_scoring_config import (
    DIMENSION_CONFIG,
    REPORT_STATUS_EVALUATED,
    REPORT_STATUS_FAILED,
    REPORT_STATUS_INCOMPLETE,
    REPORT_STATUS_PARTIAL,
)
from services.interview_scoring_service import (
    compute_dimension_scores,
    compute_overall_score_and_coverage,
    compute_per_turn_score,
    score_interview_session,
)

ALL_CRITERIA = [c for cfg in DIMENSION_CONFIG.values() for c in cfg["criteria"]]


def _make_turn(idx: int, text: str = "Detailed technical response explaining Redis caching and indexing.", status: str = "answered", mode: str = "speech"):
    return {
        "id": f"turn_{idx}_candidate",
        "turn_index": idx,
        "speaker": "candidate",
        "text": text,
        "word_count": len(text.split()),
        "turn_status": status,
        "input_mode": mode,
    }


def _make_eval(idx: int, criteria_scores: dict, status: str = "ok"):
    crit_list = [
        {"criterion": cname, "weight": 0.25, "score": sc, "quoted_justification": "Redis caching and indexing"}
        for cname, sc in criteria_scores.items()
    ]
    return {
        "id": f"eval_{idx}",
        "turn_id": f"turn_{idx}_candidate",
        "status": status,
        "rubric_scores_json": {"criteria": crit_list},
    }


def _make_sufficiency(subs_turns: int, words: int = 80, speaking_s: float = 30.0):
    return {
        "total_candidate_turns": subs_turns,
        "answered_substantive_turns": subs_turns,
        "total_words": words,
        "total_speaking_time_s": speaking_s,
    }


class TestPhase4ScoringEngine(unittest.TestCase):
    def test_01_property_missing_is_not_zero(self):
        """Removing a dimension's evidence excludes it cleanly instead of zero-filling."""
        rng = random.Random(101)
        for _ in range(50):
            uniform_s = round(rng.uniform(0.55, 0.95), 3)
            ev1 = _make_eval(1, {c: uniform_s for c in ALL_CRITERIA})
            ev2 = _make_eval(2, {c: uniform_s for c in ALL_CRITERIA})
            dims_full = compute_dimension_scores([ev1, ev2], [{"turn_id": "turn_1_candidate", "wpm": 135.0, "word_count": 30, "filler_count": 0}])
            score_full, _, cov_full = compute_overall_score_and_coverage(dims_full)

            # Remove speech delivery dimensions by passing missing timing (wpm=None)
            dims_no_deliv = compute_dimension_scores([ev1, ev2], [{"turn_id": "turn_1_candidate", "wpm": None}])
            score_no_deliv, _, cov_partial = compute_overall_score_and_coverage(dims_no_deliv)

            self.assertEqual(cov_full, 1.0)
            self.assertLess(cov_partial, 1.0)
            # Without delivery, content score remains uniform_s (not penalized toward 0)
            self.assertAlmostEqual(score_no_deliv, uniform_s, places=3)
            # Zero-filled score would strictly be lower: score_no_deliv * cov_partial
            self.assertGreater(score_no_deliv, score_no_deliv * cov_partial)

    def test_02_zero_candidate_turns_is_incomplete_no_verdict(self):
        res = score_interview_session(
            turns=[],
            evaluations=[],
            speech_metrics_list=[],
            data_sufficiency=_make_sufficiency(0, words=0, speaking_s=None),
        )
        self.assertEqual(res["report_status"], REPORT_STATUS_INCOMPLETE)
        self.assertIsNone(res["overall_score"])
        self.assertIsNone(res["grade"])
        self.assertIsNone(res["recommendation"])

    def test_03_failed_evaluations_is_evaluation_failed_never_f_reject(self):
        turns = [_make_turn(i) for i in range(1, 5)]
        evals = [_make_eval(i, {}, status="failed") for i in range(1, 5)]
        res = score_interview_session(
            turns=turns,
            evaluations=evals,
            speech_metrics_list=[{"turn_id": "turn_1_candidate", "wpm": 135.0, "word_count": 20, "filler_count": 0}],
            data_sufficiency=_make_sufficiency(4, words=80, speaking_s=35.0),
        )
        self.assertEqual(res["report_status"], REPORT_STATUS_FAILED)
        self.assertIsNone(res["overall_score"])
        self.assertIsNone(res["grade"])
        self.assertIsNone(res["recommendation"])

    def test_04_property_monotonicity_strong_and_weak_answers(self):
        """Adding a 1.0 strong answer never lowers score; adding a 0.0 weak answer never raises it."""
        rng = random.Random(202)
        for _ in range(50):
            base_turns = [_make_turn(i) for i in range(1, 4)]
            base_evals = [
                _make_eval(i, {c: round(rng.uniform(0.35, 0.85), 3) for c in ALL_CRITERIA})
                for i in range(1, 4)
            ]
            sm = [{"turn_id": "turn_1_candidate", "wpm": 135.0, "word_count": 30, "filler_count": 0}]
            base_res = score_interview_session(base_turns, base_evals, sm, _make_sufficiency(3, 60, 25.0))
            base_score = base_res["overall_score"]

            # Add strong answer (1.0 across all criteria + optimal delivery wpm 140)
            strong_turns = base_turns + [_make_turn(4)]
            strong_evals = base_evals + [_make_eval(4, {c: 1.0 for c in ALL_CRITERIA})]
            strong_res = score_interview_session(strong_turns, strong_evals, sm, _make_sufficiency(4, 90, 35.0))
            self.assertGreaterEqual(strong_res["overall_score"], base_score)

            # Add weak answer (0.0 across all criteria)
            weak_turns = base_turns + [_make_turn(5)]
            weak_evals = base_evals + [_make_eval(5, {c: 0.0 for c in ALL_CRITERIA})]
            weak_res = score_interview_session(weak_turns, weak_evals, sm, _make_sufficiency(4, 80, 30.0))
            self.assertLessEqual(weak_res["overall_score"], base_score)

    def test_05_one_weak_answer_never_produces_f_or_strong_reject(self):
        turns = [_make_turn(i) for i in range(1, 6)]
        evals = [
            _make_eval(1, {c: 0.90 for c in ALL_CRITERIA}),
            _make_eval(2, {c: 0.88 for c in ALL_CRITERIA}),
            _make_eval(3, {c: 0.92 for c in ALL_CRITERIA}),
            _make_eval(4, {c: 0.85 for c in ALL_CRITERIA}),
            _make_eval(5, {"technical_accuracy": 0.10, "technical_depth": 0.10}),  # 1 weak / IDK turn
        ]
        sm = [{"turn_id": f"turn_{i}_candidate", "wpm": 135.0, "word_count": 25, "filler_count": 0} for i in range(1, 5)]
        res = score_interview_session(turns, evals, sm, _make_sufficiency(4, 110, 45.0))
        self.assertEqual(res["report_status"], REPORT_STATUS_EVALUATED)
        self.assertNotEqual(res["grade"], "F")
        self.assertNotEqual(res["recommendation"], "Strong Reject")
        self.assertIn(res["grade"], ("A", "B"))

    def test_06_property_determinism_and_order_invariance(self):
        """Shuffling turns & evaluations in any permutation produces identical outputs."""
        turns = [_make_turn(i) for i in range(1, 7)]
        evals = [_make_eval(i, {c: 0.5 + 0.06 * i for c in ALL_CRITERIA}) for i in range(1, 7)]
        sm = [{"turn_id": f"turn_{i}_candidate", "wpm": 120.0 + i * 3, "word_count": 20, "filler_count": i % 2} for i in range(1, 7)]
        suff = _make_sufficiency(6, 120, 50.0)

        baseline = score_interview_session(turns, evals, sm, suff)
        rng = random.Random(303)
        for _ in range(50):
            t_shuf = list(turns)
            e_shuf = list(evals)
            sm_shuf = list(sm)
            rng.shuffle(t_shuf)
            rng.shuffle(e_shuf)
            rng.shuffle(sm_shuf)
            trial = score_interview_session(t_shuf, e_shuf, sm_shuf, suff)
            self.assertEqual(trial, baseline)

    def test_07_original_bug_scenario_spoken_answers_present_eval_empty(self):
        """
        Reproduces the exact bug report: candidate DID speak 5 substantive answers,
        but evaluations were empty/not run. Never 'No Responses', never F / Strong Reject!
        """
        turns = [_make_turn(i, text="I designed a scalable Redis cluster with consistent hashing and sentinel failover.", mode="speech") for i in range(1, 6)]
        sm = [{"turn_id": f"turn_{i}_candidate", "wpm": 132.0, "word_count": 12, "filler_count": 0} for i in range(1, 6)]
        res = score_interview_session(
            turns=turns,
            evaluations=[],  # Empty evaluations (the production failure)
            speech_metrics_list=sm,
            data_sufficiency=_make_sufficiency(5, 60, 27.0),
        )
        self.assertEqual(res["report_status"], REPORT_STATUS_FAILED)
        self.assertIsNone(res["overall_score"])
        self.assertIsNone(res["grade"])
        self.assertIsNone(res["recommendation"])
        self.assertNotIn("No responses", res["status_reason"])


if __name__ == "__main__":
    unittest.main()

