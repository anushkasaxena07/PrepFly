"""
Adaptive Interview Engine: Deterministic next-action policies, session knowledge map,
difficulty calibration, and anti-repetition guards for Ava AI interviews.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Deterministic adaptive decisions
DECISION_FOLLOW_UP = "FOLLOW_UP"
DECISION_CLARIFY = "CLARIFY"
DECISION_SIMPLIFY = "SIMPLIFY"
DECISION_INCREASE_DIFFICULTY = "INCREASE_DIFFICULTY"
DECISION_CHANGE_TOPIC = "CHANGE_TOPIC"
DECISION_NEXT_QUESTION = "NEXT_QUESTION"
DECISION_END_INTERVIEW = "END_INTERVIEW"


class AdaptiveInterviewEngine:
    """Orchestrates dynamic adaptation, knowledge mapping, and difficulty adjustment."""

    @staticmethod
    def evaluate_next_action(
        accuracy_score: int,
        concept_analysis: Dict[str, Any],
        turn_number: int,
        total_questions: int = 10,
        consecutive_struggles: int = 0,
        recent_followups_count: int = 0
    ) -> str:
        """
        Deterministic decision policy determining Ava's next conversational action.
        - High score (>= 85) + zero missed concepts -> INCREASE_DIFFICULTY
        - High score (>= 70) + partially understood or missing concept -> FOLLOW_UP (capped at 2)
        - Moderate score (50-69) -> FOLLOW_UP or CLARIFY
        - Low score (< 50) + repeated struggle -> SIMPLIFY
        - Turn limit reached -> END_INTERVIEW
        """
        if turn_number >= total_questions:
            return DECISION_END_INTERVIEW

        # Cap follow-ups to 2 per topic so the candidate is not stuck in an endless loop
        if recent_followups_count >= 2:
            return DECISION_CHANGE_TOPIC

        if accuracy_score >= 85 and not concept_analysis.get("missing_concepts"):
            return DECISION_INCREASE_DIFFICULTY

        if 65 <= accuracy_score < 85 and concept_analysis.get("partially_understood_concepts"):
            return DECISION_FOLLOW_UP

        if 40 <= accuracy_score < 65:
            if concept_analysis.get("word_count", 0) < 10:
                return DECISION_CLARIFY
            return DECISION_FOLLOW_UP

        if accuracy_score < 40:
            if consecutive_struggles >= 1:
                return DECISION_SIMPLIFY
            return DECISION_CLARIFY

        return DECISION_NEXT_QUESTION

    @staticmethod
    def update_session_knowledge_map(
        current_map: Dict[str, Any],
        topic: str,
        subtopic: str,
        concept_analysis: Dict[str, Any],
        accuracy_score: int
    ) -> Dict[str, Any]:
        """
        Updates session-level knowledge map with verified demonstrated concepts,
        unverified gaps, and proficiency evidence.
        """
        k_map = dict(current_map or {})
        t_key = topic.lower().replace(" ", "_")
        sub_key = subtopic.lower().replace(" ", "_")

        if t_key not in k_map:
            k_map[t_key] = {}
        if sub_key not in k_map[t_key]:
            k_map[t_key][sub_key] = {
                "proficiency_evidence": "unknown",
                "concepts": {},
                "attempts": 0,
                "latest_score": accuracy_score
            }

        entry = k_map[t_key][sub_key]
        entry["attempts"] += 1
        entry["latest_score"] = accuracy_score

        if accuracy_score >= 75:
            entry["proficiency_evidence"] = "strong"
        elif accuracy_score >= 50:
            entry["proficiency_evidence"] = "moderate"
        else:
            entry["proficiency_evidence"] = "needs_improvement"

        # Update concept states
        for c in concept_analysis.get("demonstrated_concepts", []):
            entry["concepts"][c] = "demonstrated"
        for c in concept_analysis.get("partially_understood_concepts", []):
            if entry["concepts"].get(c) != "demonstrated":
                entry["concepts"][c] = "partial"
        for c in concept_analysis.get("missed_concepts", []):
            if entry["concepts"].get(c) != "demonstrated":
                entry["concepts"][c] = "unverified"

        return k_map

    @staticmethod
    def construct_adaptive_prompt_guidance(
        decision: str,
        concept_analysis: Dict[str, Any],
        personality_modifier: str,
        knowledge_map: Dict[str, Any]
    ) -> str:
        """
        Generates targeted LLM steering directives for the next question based on the decision policy.
        """
        if decision == DECISION_FOLLOW_UP:
            missing = ", ".join(concept_analysis.get("partially_understood_concepts", [])) or "the deeper mechanism"
            directive = f"DECISION: TARGETED FOLLOW-UP. The candidate explained the core concept well, but omitted {missing}. Ask a focused follow-up probing this specific aspect without repeating the premise."
        elif decision == DECISION_INCREASE_DIFFICULTY:
            directive = "DECISION: INCREASE DIFFICULTY. The candidate demonstrated comprehensive mastery. Escalate to a complex production scenario, worst-case trade-off, or failure mode."
        elif decision == DECISION_SIMPLIFY:
            directive = "DECISION: SIMPLIFY. The candidate struggled on this question. Step back to test foundational prerequisite concepts or offer a simpler concrete scenario."
        elif decision == DECISION_CLARIFY:
            directive = "DECISION: CLARIFICATION. The candidate's response was ambiguous or brief. Acknowledge and ask them to elaborate on their thought process."
        elif decision == DECISION_CHANGE_TOPIC:
            directive = "DECISION: CHANGE TOPIC. Topic sufficiently explored. Smoothly transition to the next technical pillar for this role."
        else:
            directive = "DECISION: NEXT QUESTION. Progress naturally to the next question in the interview round."

        return f"""═══════════════════════════════
ADAPTIVE ENGINE DIRECTIVE
═══════════════════════════════
{directive}

{personality_modifier}"""

