"""
Answer Analyzer: Conversational intent detection, concept-level evaluation,
evidence extraction, and semantic analysis for candidate responses.
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

INTENT_REPEAT = "REPEAT"
INTENT_CLARIFY = "CLARIFY"
INTENT_PAUSE = "PAUSE"
INTENT_NO_ANSWER = "NO_ANSWER"
INTENT_CORRECTION = "CORRECTION"
INTENT_EARLY_EXIT = "EARLY_EXIT"
INTENT_ANSWER = "ANSWER"

CONVERSATIONAL_INTENT_PATTERNS = [
    (INTENT_REPEAT, [
        r'\b(?:repeat|pardon|say\s+again|didn\'?t\s+hear|could\s+you\s+repeat|can\s+you\s+repeat)\b'
    ]),
    (INTENT_CLARIFY, [
        r'\b(?:what\s+do\s+you\s+mean|can\s+you\s+explain|could\s+you\s+clarify|can\s+i\s+ask|what\s+does\s+that\s+mean)\b'
    ]),
    (INTENT_PAUSE, [
        r'\b(?:let\s+me\s+think|give\s+me\s+a\s+moment|give\s+me\s+a\s+sec|one\s+second|thinking\s+for\s+a\s+moment|can\s+i\s+think)\b'
    ]),
    (INTENT_NO_ANSWER, [
        r'\b(?:i\s+don\'?t\s+know|not\s+sure|no\s+idea|i\'m\s+blank|skip\s+this|pass\s+on\s+this)\b'
    ]),
    (INTENT_CORRECTION, [
        r'\b(?:let\s+me\s+correct|wait\s+actually|to\s+correct\s+what\s+i\s+said|correction|actually\s+wait)\b'
    ]),
    (INTENT_EARLY_EXIT, [
        r'\b(?:end\s+(?:the\s+)?interview|stop\s+(?:the\s+)?interview|i\s+want\s+to\s+quit|can\s+i\s+exit|wrap\s+up\s+early)\b'
    ])
]


class AnswerAnalyzer:
    """Analyzes candidate speech/text for conversational intent, concepts, and evidence."""

    @staticmethod
    def detect_conversational_intent(answer_text: str) -> str:
        """
        Detects if candidate's response is a conversational command (repeat, clarify, pause, etc.)
        rather than a technical answer.
        """
        if not answer_text or not answer_text.strip():
            return INTENT_NO_ANSWER

        cleaned = answer_text.strip().lower()
        # If very short or exact phrase match
        for intent, patterns in CONVERSATIONAL_INTENT_PATTERNS:
            for pat in patterns:
                if re.search(pat, cleaned):
                    # For PAUSE or REPEAT or CLARIFY, if answer is very short (under 15 words), treat as command
                    words = cleaned.split()
                    if len(words) <= 15:
                        return intent
                    # If long answer that mentions 'repeat' in passing, treat as ANSWER
                    if intent in (INTENT_REPEAT, INTENT_PAUSE, INTENT_CLARIFY) and len(words) > 20:
                        continue
                    return intent

        return INTENT_ANSWER

    @staticmethod
    def extract_concept_evidence(question: str, answer: str, category: str = "", role: str = "") -> Dict[str, Any]:
        """
        Extracts demonstrated concepts, missed concepts, and supporting evidence citations.
        Evaluates strictly against question context without fabricating knowledge gaps.
        """
        ans_lower = answer.lower().strip()
        words = re.findall(r'\b[a-z]{3,}\b', ans_lower)
        word_count = len(words)

        demonstrated = []
        partially_understood = []
        missed = []
        misconceptions = []
        supporting_citations = []

        # Common concept dictionaries by domain
        q_lower = question.lower()
        if "stack" in q_lower or "heap" in q_lower or "memory" in q_lower:
            if "stack" in ans_lower:
                demonstrated.append("stack_memory")
                supporting_citations.append("Mentioned stack memory for execution/local variables")
            if "heap" in ans_lower:
                demonstrated.append("heap_memory")
                supporting_citations.append("Mentioned heap memory for dynamic objects")
            if "reference" in ans_lower or "counting" in ans_lower:
                demonstrated.append("reference_counting")
            else:
                partially_understood.append("garbage_collection_internals")
            if "cyclic" in ans_lower or "cycle" in ans_lower:
                demonstrated.append("cyclic_garbage_collection")

        elif "hash" in q_lower or "map" in q_lower or "table" in q_lower:
            if "collision" in ans_lower or "chaining" in ans_lower or "probing" in ans_lower:
                demonstrated.append("collision_resolution")
            if "o(1)" in ans_lower or "constant" in ans_lower:
                demonstrated.append("amortized_lookup_time")
            if "load factor" in ans_lower or "rehashing" in ans_lower:
                demonstrated.append("rehashing_dynamics")
            else:
                partially_understood.append("rehashing_and_load_factor")

        elif "tree" in q_lower or "bst" in q_lower:
            if "left" in ans_lower and "right" in ans_lower:
                demonstrated.append("binary_search_tree_property")
            if "o(log n)" in ans_lower or "height" in ans_lower:
                demonstrated.append("tree_traversal_complexity")
            if "balance" in ans_lower or "avl" in ans_lower or "red black" in ans_lower:
                demonstrated.append("balanced_trees")
            else:
                partially_understood.append("self_balancing_trees")

        elif "concurrency" in q_lower or "thread" in q_lower or "process" in q_lower:
            if "share" in ans_lower and "memory" in ans_lower:
                demonstrated.append("shared_memory_space")
            if "deadlock" in ans_lower or "mutex" in ans_lower or "lock" in ans_lower:
                demonstrated.append("synchronization_primitives")
            if "context switch" in ans_lower:
                demonstrated.append("context_switching_overhead")

        # General concept extraction based on substantive keyword matches
        if not demonstrated and word_count >= 15:
            demonstrated.append("core_domain_principles")
            supporting_citations.append(answer[:120].strip() + "...")

        # Detect clear misconceptions (e.g., claiming stack is for dynamic objects, or hash lookup is always O(N))
        if "stack" in q_lower and "stack stores objects dynamically" in ans_lower:
            misconceptions.append("Confused stack memory with heap memory allocation.")

        return {
            "demonstrated_concepts": demonstrated,
            "partially_understood_concepts": partially_understood,
            "missed_concepts": missed,
            "misconceptions": misconceptions,
            "supporting_citations": supporting_citations,
            "word_count": word_count,
            "confidence_estimate": "high" if word_count >= 25 and demonstrated else ("medium" if word_count >= 12 else "low")
        }

    @staticmethod
    def generate_conversational_response_for_intent(intent: str, last_question: str, personality_key: str = "professional") -> Dict[str, Any]:
        """
        Generates a human-like, in-character reaction when candidate issues a conversational command.
        """
        if intent == INTENT_REPEAT:
            return {
                "message": f"Sure thing! Let me repeat that: {last_question}",
                "action": "REPEAT",
                "done": False
            }
        elif intent == INTENT_CLARIFY:
            return {
                "message": f"Certainly. To clarify: I am looking for your thought process, key trade-offs, and how you would structure the solution in a production environment.",
                "action": "CLARIFY",
                "done": False
            }
        elif intent == INTENT_PAUSE:
            return {
                "message": "Take your time. Whenever you're ready, please go ahead.",
                "action": "PAUSE",
                "done": False
            }
        elif intent == INTENT_NO_ANSWER:
            return {
                "message": "No problem at all — let's move forward to the next area.",
                "action": "SKIP",
                "done": False
            }
        elif intent == INTENT_CORRECTION:
            return {
                "message": "Of course, go right ahead and share your revised thoughts.",
                "action": "CORRECTION",
                "done": False
            }
        elif intent == INTENT_EARLY_EXIT:
            return {
                "message": "Understood. We will conclude the session here and compile your feedback report based on the completed questions.",
                "action": "EARLY_EXIT",
                "done": True
            }
        return {
            "message": "Understood. Let's proceed.",
            "action": "PROCEED",
            "done": False
        }
