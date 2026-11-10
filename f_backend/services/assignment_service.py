"""
Assignment Service for PrepFly Adaptive AI Interview Mentor.
Derives real-world technical assignments from (skill gap, observed misconception,
target role, difficulty level).
Produces concrete deliverables, dataset specifications with deterministic seeds,
explicit rubric weights summing to 1.0, and hidden tests for automated sandbox verification.
"""

from typing import Dict, List, Optional, Any
import hashlib
import random
import uuid

from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG


class AssignmentService:
    """Generates concrete, deliverable-focused assignments conditioned on candidate skill gaps."""

    @classmethod
    def generate_assignment(
        cls,
        skill_id: str,
        misconception: Optional[str] = None,
        target_role: str = "Software Engineer",
        difficulty: str = "intermediate",
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes a concrete technical assignment with requirements, dataset specs,
        rubrics, and hidden sandbox tests.
        """
        skill_info = SkillTaxonomyService.get_skill(skill_id) or {}
        sname = skill_info.get("name", skill_id.replace("_", " ").title())
        diff_norm = difficulty.lower()

        # Deterministic seed if provided or derived from skill_id
        active_seed = seed if seed is not None else int(hashlib.md5(f"{skill_id}:{diff_norm}".encode()).hexdigest()[:8], 16)
        rng = random.Random(active_seed)

        # 1. Specialized Domain: AI/ML Imbalanced Classification & Evaluation
        if skill_id in ("ml_model_evaluation", "ml_model_development", "dl_frameworks_pytorch_tensorflow") or "ml" in skill_id:
            return cls._build_aiml_classification_assignment(skill_id, sname, misconception, diff_norm, rng)

        # 2. Specialized Domain: System Design & Databases
        if skill_id in ("sys_db_design", "sys_caching", "cs_dbms", "cs_concurrency") or "sys_" in skill_id:
            return cls._build_systems_assignment(skill_id, sname, misconception, diff_norm, rng)

        # 3. Canonical Algorithmic & Engineering Assignment
        return cls._build_canonical_assignment(skill_id, sname, misconception, diff_norm, rng)

    @classmethod
    def _build_aiml_classification_assignment(
        cls,
        skill_id: str,
        skill_name: str,
        misconception: Optional[str],
        difficulty: str,
        rng: random.Random
    ) -> Dict[str, Any]:
        """Imbalanced classification task with preprocessing, metrics, and trade-off analysis."""
        skew_ratio = rng.choice(["99:1", "95:5", "98:2"])
        asg_id = f"asg_aiml_{uuid.uuid4().hex[:8]}"

        misconception_prompt = ""
        if misconception:
            misconception_prompt = f" Note: Pay explicit attention to avoiding prior misconceptions regarding '{misconception}'."

        hidden_tests = [
            {
                "test_id": "test_empty_case",
                "code": "assert evaluate_classifier([], []) == {'status': 'error', 'message': 'empty_input'}"
            },
            {
                "test_id": "test_all_negative_baseline",
                "code": (
                    "y_true = [0] * 99 + [1]\n"
                    "y_pred = [0] * 100\n"
                    "res = evaluate_classifier(y_true, y_pred)\n"
                    "assert res['accuracy'] == 0.99 and res['recall'] == 0.0, 'Accuracy paradox failed'"
                )
            },
            {
                "test_id": "test_balanced_metrics",
                "code": (
                    "y_true = [0, 0, 1, 1]\n"
                    "y_pred = [0, 1, 0, 1]\n"
                    "res = evaluate_classifier(y_true, y_pred)\n"
                    "assert res['f1'] == 0.5, f'F1 mismatch: {res[\"f1\"]}'"
                )
            }
        ]

        starter_code = (
            "def evaluate_classifier(y_true, y_pred):\n"
            "    \"\"\"\n"
            "    Calculates precision, recall, F1, and accuracy under class skew.\n"
            "    Returns dict with keys: 'accuracy', 'precision', 'recall', 'f1', 'status'\n"
            "    \"\"\"\n"
            "    if not y_true or not y_pred:\n"
            "        return {'status': 'error', 'message': 'empty_input'}\n"
            "    # Your implementation here\n"
            "    pass\n"
        )

        return {
            "assignment_id": asg_id,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "title": f"Extreme Skew ({skew_ratio}) Classification & Metric Optimization",
            "difficulty": difficulty,
            "learning_objective": f"Master evaluation metrics (PR-AUC vs ROC-AUC) and loss weighting under severe {skew_ratio} class imbalance.",
            "requirements": [
                f"Implement `evaluate_classifier(y_true, y_pred)` to compute precision, recall, F1, and accuracy.",
                f"Address the accuracy paradox: explain why a naive 99% accuracy baseline provides zero recall on minority fraud/anomaly classes.{misconception_prompt}",
                f"Explain trade-offs between precision-recall AUC and ROC-AUC under extreme skew.",
                f"Formulate a threshold adjustment strategy prioritizing recall over precision."
            ],
            "deliverables": [
                "Executable Python implementation of `evaluate_classifier` passing hidden test suite.",
                "Technical justification explaining metric selection, false positive costs, and threshold trade-offs."
            ],
            "dataset_spec": {
                "format": "Binary target arrays (0 = majority, 1 = minority)",
                "skew_ratio": skew_ratio,
                "n_samples": 10000,
                "seed": rng.randint(1000, 9999)
            },
            "constraints": "O(N) time complexity, O(1) auxiliary space beyond return dict.",
            "rubric": {
                "correctness": 0.30,
                "technical_depth": 0.25,
                "implementation_quality": 0.20,
                "tradeoff_analysis": 0.15,
                "communication": 0.10
            },
            "starter_code": starter_code,
            "hidden_tests": hidden_tests,
            "time_estimate_minutes": 35
        }

    @classmethod
    def _build_systems_assignment(
        cls,
        skill_id: str,
        skill_name: str,
        misconception: Optional[str],
        difficulty: str,
        rng: random.Random
    ) -> Dict[str, Any]:
        """Systems / database assignment with concurrency and idempotency constraints."""
        asg_id = f"asg_sys_{uuid.uuid4().hex[:8]}"

        hidden_tests = [
            {
                "test_id": "test_empty_payload",
                "code": "assert process_idempotent_event('', {}) == {'status': 'rejected', 'reason': 'missing_idempotency_key'}"
            },
            {
                "test_id": "test_idempotent_replay",
                "code": (
                    "k = 'txn_9918'\n"
                    "r1 = process_idempotent_event(k, {'amount': 100})\n"
                    "r2 = process_idempotent_event(k, {'amount': 100})\n"
                    "assert r1['status'] == 'processed' and r2['status'] == 'replayed' and r2['cached_result'] == r1['result'], 'Idempotency failed'"
                )
            }
        ]

        starter_code = (
            "_IDEMPOTENCY_STORE = {}\n\n"
            "def process_idempotent_event(idempotency_key, event_payload):\n"
            "    \"\"\"\n"
            "    Enforces exactly-once execution for mutations.\n"
            "    Returns dict with keys: 'status' ('processed' or 'replayed'), 'result'\n"
            "    \"\"\"\n"
            "    if not idempotency_key:\n"
            "        return {'status': 'rejected', 'reason': 'missing_idempotency_key'}\n"
            "    # Your implementation here\n"
            "    pass\n"
        )

        return {
            "assignment_id": asg_id,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "title": f"Production Idempotency & Replay Defense: {skill_name}",
            "difficulty": difficulty,
            "learning_objective": f"Design and implement replay-safe mutation processing preserving database consistency.",
            "requirements": [
                "Implement `process_idempotent_event(idempotency_key, event_payload)`.",
                "Prevent race conditions when duplicate concurrent mutations arrive within 10ms.",
                "Explain the trade-offs between Redis distributed locks vs PostgreSQL unique constraints for deduplication."
            ],
            "deliverables": [
                "Executable Python implementation handling deduplication and replays.",
                "Concurrency and split-brain mitigation explanation."
            ],
            "dataset_spec": {
                "format": "Transaction mutation events with UUID idempotency keys",
                "traffic_profile": "Burst mutations with 15% duplicate replay rate"
            },
            "constraints": "Thread-safe execution with bounded TTL expiration.",
            "rubric": {
                "correctness": 0.35,
                "technical_depth": 0.25,
                "implementation_quality": 0.20,
                "tradeoff_analysis": 0.10,
                "communication": 0.10
            },
            "starter_code": starter_code,
            "hidden_tests": hidden_tests,
            "time_estimate_minutes": 40
        }

    @classmethod
    def _build_canonical_assignment(
        cls,
        skill_id: str,
        skill_name: str,
        misconception: Optional[str],
        difficulty: str,
        rng: random.Random
    ) -> Dict[str, Any]:
        """Canonical algorithmic deliverable."""
        asg_id = f"asg_core_{uuid.uuid4().hex[:8]}"

        hidden_tests = [
            {
                "test_id": "test_empty_input",
                "code": f"assert solve_{skill_id}([]) == []"
            },
            {
                "test_id": "test_single_element",
                "code": f"assert len(solve_{skill_id}([42])) == 1"
            }
        ]

        starter_code = (
            f"def solve_{skill_id}(input_list):\n"
            f"    \"\"\"\n"
            f"    Production implementation of {skill_name}.\n"
            f"    Complexity: O(N) Time, O(1) Auxiliary Space.\n"
            f"    \"\"\"\n"
            f"    if not input_list:\n"
            f"        return []\n"
            f"    # Your implementation here\n"
            f"    return input_list\n"
        )

        return {
            "assignment_id": asg_id,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "title": f"Applied Implementation Challenge: {skill_name}",
            "difficulty": difficulty,
            "learning_objective": f"Implement and prove asymptotic bounds for {skill_name}.",
            "requirements": [
                f"Implement `solve_{skill_id}(input_list)` preserving asymptotic bounds.",
                "Handle boundary edge cases: empty lists, duplicates, and extreme ranges.",
                "Provide formal Big-O time and space complexity derivation."
            ],
            "deliverables": [
                f"Python function `solve_{skill_id}` passing all hidden tests.",
                "Complexity derivation and edge case analysis."
            ],
            "dataset_spec": {"type": "Ordered and unordered test arrays", "seed": rng.randint(100, 999)},
            "constraints": "O(N) time complexity, O(1) auxiliary space.",
            "rubric": {
                "correctness": 0.40,
                "technical_depth": 0.30,
                "implementation_quality": 0.20,
                "communication": 0.10
            },
            "starter_code": starter_code,
            "hidden_tests": hidden_tests,
            "time_estimate_minutes": 30
        }

