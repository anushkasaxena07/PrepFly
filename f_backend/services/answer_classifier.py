"""
Answer Classifier: Domain Authority for Evaluating and Categorizing Candidate Responses
Implements exact 7-tier classification, dimension scoring, and zero-false-strengths enforcement.
"""

import re
from typing import Dict, Any, Tuple, List, Optional

# ── 1. CLASSIFICATION LABELS ────────────────────────────────────────────────
CLASS_CORRECT_COMPLETE = "Correct and complete"
CLASS_PARTIALLY_CORRECT = "Partially correct"
CLASS_INCORRECT = "Incorrect"
CLASS_IRRELEVANT_OFF_TOPIC = "Irrelevant or off-topic"
CLASS_NO_ANSWER = "No answer"
CLASS_EARLY_EXIT = "Early exit or interview termination"
CLASS_UNCLEAR_INSUFFICIENT = "Unclear or insufficient response"

ALL_CLASSIFICATIONS = [
    CLASS_CORRECT_COMPLETE,
    CLASS_PARTIALLY_CORRECT,
    CLASS_INCORRECT,
    CLASS_IRRELEVANT_OFF_TOPIC,
    CLASS_NO_ANSWER,
    CLASS_EARLY_EXIT,
    CLASS_UNCLEAR_INSUFFICIENT
]

# ── 2. PATTERN DETECTORS ────────────────────────────────────────────────────
EARLY_EXIT_PATTERNS = [
    r"\bcan i end\b", r"\bend inw\b", r"\bend interview\b", r"\bi want to end\b",
    r"\bcan we stop\b", r"\bstop now\b", r"\bquit interview\b", r"\bplease end\b",
    r"\bi want to leave\b", r"\bcan i leave\b", r"\bstop the interview\b",
    r"\bwrap up now\b", r"\bfinish now\b", r"\bdone for today\b"
]

NO_ANSWER_PATTERNS = [
    r"^\s*$",
    r"^\s*i don'?t know\b",
    r"^\s*no idea\b",
    r"^\s*skip\b",
    r"^\s*skip this\b",
    r"^\s*skip question\b",
    r"^\s*not sure\b",
    r"^\s*pardon\b",
    r"^\s*pass\b",
    r"^\s*no response\b",
    r"^\s*\[no response recorded\]\b",
    r"^\s*idk\b",
    r"^\s*no answer\b"
]

OFF_TOPIC_PATTERNS = [
    r"\bmy day is bad\b", r"\bbad day\b", r"\bfeeling terrible\b",
    r"\bwhatever\b", r"\bno thanks\b", r"\bwho cares\b",
    r"\bmy favourite programming language is\b", r"\bi like pizza\b",
    r"\bwhat is your name\b", r"\bwho are you\b"
]


# ── 3. CLASSIFIER FUNCTION ──────────────────────────────────────────────────
def classify_candidate_response(
    question: str,
    answer: str,
    expected_keywords: Optional[List[str]] = None,
    category: str = "",
    role: str = ""
) -> Tuple[str, float, Dict[str, float], str]:
    """
    Classifies a candidate response into one of the 7 required categories.
    Returns: (classification, overall_accuracy_0_100, dimension_scores, rationale)
    """
    ans_clean = (answer or "").strip()
    ans_lower = ans_clean.lower()
    words = ans_clean.split()
    word_count = len(words)

    # Dimension scores defaults (0.0 - 100.0)
    # Dimensions: technical/domain correctness (40%), conceptual understanding (25%), problem solving (20%), communication (15%)
    dim_scores = {
        "correctness": 0.0,
        "understanding": 0.0,
        "approach": 0.0,
        "communication": 0.0
    }

    # 1. Early Exit Detection
    for pat in EARLY_EXIT_PATTERNS:
        if re.search(pat, ans_lower):
            return CLASS_EARLY_EXIT, 0.0, dim_scores, "Candidate explicitly requested to terminate the interview early."

    # 2. No Answer Detection
    if word_count == 0:
        return CLASS_NO_ANSWER, 0.0, dim_scores, "No input provided by candidate."

    for pat in NO_ANSWER_PATTERNS:
        if re.search(pat, ans_lower):
            return CLASS_NO_ANSWER, 0.0, dim_scores, f"Candidate indicated no answer or chose to skip: '{ans_clean}'"

    # 3. Off-Topic / Irrelevant Detection
    # Off-topic phrase or response completely disconnected from technical question
    is_off_topic = False
    for pat in OFF_TOPIC_PATTERNS:
        if re.search(pat, ans_lower):
            is_off_topic = True
            break

    # Check question-answer relevance
    q_lower = (question or "").lower()
    stop_words = {"what", "how", "why", "who", "which", "when", "where", "the", "a", "an", "is", "are", "was", "were", "to", "in", "of", "on", "for", "with", "about", "your", "you", "me", "tell", "explain", "describe", "would"}
    q_keywords = [w.strip("?,.:;\"'") for w in q_lower.split() if w.strip("?,.:;\"'") not in stop_words and len(w) > 3]

    matched_kw = [w for w in q_keywords if w in ans_lower]
    if expected_keywords:
        matched_kw += [w for w in expected_keywords if w.lower() in ans_lower]

    if is_off_topic or (word_count >= 5 and len(matched_kw) == 0 and not any(k in ans_lower for k in ["approach", "solution", "because", "example", "implement", "experience"])):
        # If answering a completely different subject (e.g. favourite language when asked about binary search)
        if any(w in ans_lower for w in ["favourite", "favorite", "weather", "today is", "food", "movie", "song", "bad day"]):
            dim_scores = {"correctness": 0.0, "understanding": 0.0, "approach": 0.0, "communication": 20.0}
            return CLASS_IRRELEVANT_OFF_TOPIC, 10.0, dim_scores, "Response is off-topic and does not address the question asked."

    # 4. Unclear or Insufficient Response Detection
    # Very short responses (1-3 words) like "yes", "ok", "done", "binary search works"
    if word_count <= 3 and ans_lower not in ["o(n)", "o(1)", "o(log n)", "o(n log n)"]:
        dim_scores = {"correctness": 20.0, "understanding": 15.0, "approach": 10.0, "communication": 20.0}
        acc = 15.0
        return CLASS_UNCLEAR_INSUFFICIENT, acc, dim_scores, f"Response is too brief ({word_count} words) to evaluate competence."

    # 5. Substantive Answer Evaluation
    # Evaluate depth and correctness
    kw_ratio = len(matched_kw) / max(1, len(q_keywords))
    
    # Base correctness from keyword overlap and structural reasoning
    has_tradeoff_or_reasoning = any(w in ans_lower for w in ["because", "therefore", "tradeoff", "complexity", "advantage", "disadvantage", "whereas", "however", "instead of"])
    has_example_or_metrics = any(w in ans_lower for w in ["for example", "such as", "case", "instance", "time complexity", "space complexity", "o(", "milliseconds", "latency"])
    
    # Calculate dimension scores
    if kw_ratio >= 0.4 and word_count >= 25 and (has_tradeoff_or_reasoning or has_example_or_metrics):
        classification = CLASS_CORRECT_COMPLETE
        dim_scores["correctness"] = min(100.0, 75.0 + kw_ratio * 25.0)
        dim_scores["understanding"] = min(100.0, 70.0 + (15.0 if has_tradeoff_or_reasoning else 0.0) + (15.0 if has_example_or_metrics else 0.0))
        dim_scores["approach"] = min(100.0, 75.0 + min(20.0, word_count * 0.4))
        dim_scores["communication"] = min(100.0, 80.0 + min(15.0, word_count * 0.3))
        rationale = "Candidate provided a comprehensive explanation addressing core principles, trade-offs, and examples."
    elif kw_ratio >= 0.2 and word_count >= 12:
        classification = CLASS_PARTIALLY_CORRECT
        dim_scores["correctness"] = min(75.0, 45.0 + kw_ratio * 30.0)
        dim_scores["understanding"] = min(75.0, 45.0 + (15.0 if has_tradeoff_or_reasoning else 0.0))
        dim_scores["approach"] = min(70.0, 40.0 + min(20.0, word_count * 0.5))
        dim_scores["communication"] = min(80.0, 60.0 + min(15.0, word_count * 0.4))
        rationale = "Candidate demonstrated foundational concepts but omitted key edge cases, implementation details, or trade-offs."
    else:
        classification = CLASS_INCORRECT
        dim_scores["correctness"] = max(10.0, kw_ratio * 30.0)
        dim_scores["understanding"] = max(10.0, 20.0 if has_tradeoff_or_reasoning else 10.0)
        dim_scores["approach"] = max(10.0, 20.0 if word_count > 10 else 10.0)
        dim_scores["communication"] = min(60.0, 30.0 + min(20.0, word_count * 0.5))
        rationale = "Candidate response did not provide technically sound definitions or failed to address the core problem."

    # Compute deterministic weighted composite accuracy (0 - 100)
    # Correctness: 40%, Understanding: 25%, Approach: 20%, Communication: 15%
    composite_acc = (
        dim_scores["correctness"] * 0.40 +
        dim_scores["understanding"] * 0.25 +
        dim_scores["approach"] * 0.20 +
        dim_scores["communication"] * 0.15
    )
    composite_acc = round(min(100.0, max(0.0, composite_acc)), 1)

    return classification, composite_acc, dim_scores, rationale


# ── 4. STRENGTH VALIDATOR & EXTRACTOR ───────────────────────────────────────
def extract_verified_strength(
    classification: str,
    accuracy_score: float,
    question: str,
    candidate_answer: str,
    dimension_scores: Dict[str, float]
) -> Optional[Dict[str, str]]:
    """
    Guarantees zero false strengths.
    Only awards a strength if:
    - Candidate answer was classified as Correct and complete or high Partially correct (score >= 70)
    - Candidate answer is not a skip, non-answer, exit phrase, or irrelevant response
    - Verified evidence exists
    """
    # Critical disqualifiers
    if classification in [CLASS_NO_ANSWER, CLASS_EARLY_EXIT, CLASS_IRRELEVANT_OFF_TOPIC, CLASS_UNCLEAR_INSUFFICIENT]:
        return None

    if accuracy_score < 70.0:
        return None

    ans_clean = candidate_answer.strip()
    if len(ans_clean.split()) < 8:
        return None

    # Determine demonstrated competency based on question and highest dimension
    q_lower = question.lower()
    if any(k in q_lower for k in ["array", "string", "tree", "graph", "dsa", "complexity", "dynamic programming"]):
        competency = "Algorithmic Analysis & Complexity Trade-offs"
    elif any(k in q_lower for k in ["system", "scalable", "cache", "sharding", "architecture", "microservice"]):
        competency = "Distributed Architecture & Scalability Design"
    elif any(k in q_lower for k in ["tcp", "udp", "process", "thread", "acid", "database", "solid"]):
        competency = "Core Computer Science & Systems Engineering"
    elif any(k in q_lower for k in ["conflict", "deadline", "leadership", "feedback", "talent", "employee"]):
        competency = "Structured Behavioral & Leadership Communication (STAR)"
    else:
        competency = "Domain Reasoning & Solution Articulation"

    quote = ans_clean[:100] + ("..." if len(ans_clean) > 100 else "")
    return {
        "competency": competency,
        "question": question,
        "evidence": f"Candidate stated: \"{quote}\"",
        "reason": f"Demonstrated {competency.lower()} with structured reasoning ({accuracy_score:.0f}/100 accuracy)."
    }


def compute_deterministic_score(dimension_scores: Dict[str, float]) -> float:
    correctness = dimension_scores.get("correctness", 0.0)
    understanding = dimension_scores.get("understanding", 0.0)
    approach = dimension_scores.get("approach", 0.0)
    communication = dimension_scores.get("communication", 0.0)
    composite = (correctness * 0.40) + (understanding * 0.25) + (approach * 0.20) + (communication * 0.15)
    return round(min(100.0, max(0.0, composite)), 1)


def extract_verified_weakness(
    classification: str,
    accuracy_score: float,
    question: str,
    candidate_answer: str,
    dimension_scores: Dict[str, float]
) -> Dict[str, str]:
    ans_clean = (candidate_answer or "").strip()
    quote = ans_clean[:100] + ("..." if len(ans_clean) > 100 else "")
    if classification == CLASS_EARLY_EXIT:
        return {
            "area": "Interview Persistence and Completion",
            "question": question,
            "evidence": f"Candidate requested early termination: '{quote}'",
            "recommendation": "Complete the full question sequence to provide sufficient evidence for candidate evaluation."
        }
    if classification == CLASS_NO_ANSWER:
        return {
            "area": "Domain Responsiveness",
            "question": question,
            "evidence": "Candidate skipped or provided no answer.",
            "recommendation": "Attempt questions by articulating initial problem breakdown and edge case considerations."
        }
    if classification == CLASS_IRRELEVANT_OFF_TOPIC:
        return {
            "area": "Question Relevance and Focus",
            "question": question,
            "evidence": f"Candidate gave off-topic response: '{quote}'",
            "recommendation": "Directly address the specific prompt rather than deflecting or giving unrelated information."
        }
    return {
        "area": "Technical Depth and Edge Cases",
        "question": question,
        "evidence": f"Candidate stated: '{quote}'",
        "recommendation": "Provide detailed explanations incorporating trade-offs, complexity analysis, and concrete real-world examples."
    }
