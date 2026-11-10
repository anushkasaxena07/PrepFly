"""
Centralized Configuration for AI Interview Capture, Speech Telemetry, Evaluation, and Scoring.
Operating Rule R9: ALL thresholds, weights, minimum-answer counts, filler lists, and grade bands
live in ONE config file (no magic constants scattered across services or routes).
"""

FORMULA_VERSION = "v1"

# ── Speech & Capture Thresholds ──────────────────────────────────────────────
STT_MIN_CONFIDENCE = 0.55
MIN_SPEECH_DURATION_S = 1.0
PAUSE_GAP_THRESHOLD_S = 1.0

FILLER_WORDS = [
    "um",
    "uh",
    "er",
    "ah",
    "like",
    "basically",
    "you know",
    "actually",
    "literally",
    "sort of",
    "kind of",
]

# Pacings (WPM bounds for feedback guidance only, never fake constants)
WPM_OPTIMAL_MIN = 115.0
WPM_OPTIMAL_MAX = 160.0

# ── Turn Classification & Sufficiency Constants ──────────────────────────────
MIN_WORDS_SUBSTANTIVE = 5
SHORT_ANSWER_MAX_WORDS = 4

VALID_TURN_STATUSES = (
    "answered",
    "skipped",
    "off_topic",
    "empty",
    "stt_failed",
    "stt_low_confidence",
    "small_talk",
)

SKIP_PHRASES = {
    "skip",
    "pass",
    "next",
    "next question",
    "skip question",
    "pass on this",
    "no response",
    "[no response recorded]",
}

DONT_KNOW_PHRASES = {
    "i don't know",
    "i dont know",
    "idk",
    "no idea",
    "not sure",
    "i have no idea",
    "i don't remember",
    "i am not sure",
}

SMALL_TALK_PHRASES = {
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "how are you",
    "how are you doing",
    "i am doing well",
    "doing great",
    "ready",
    "i am ready",
    "yes ready",
    "thank you",
    "thanks",
}

# ── Evaluation & Scoring Constants (Used in Phases 3, 4, 5) ──────────────────
MIN_TURNS_PER_DIMENSION = 2
MIN_SUBSTANTIVE_TURNS_FOR_PARTIAL = 1
MIN_SUBSTANTIVE_TURNS_FOR_EVALUATED = 3
MIN_SUBSTANTIVE_TURNS_FOR_STRONG_REJECT = 3
MIN_WORDS_FOR_PARTIAL = 15
MIN_COVERAGE_FOR_PARTIAL = 0.25
MIN_COVERAGE_FOR_ESTABLISHED = 0.75

STRENGTH_THRESHOLD = 0.75
WEAKNESS_THRESHOLD = 0.60
DOUBLE_GRADE_DISAGREEMENT_THRESHOLD = 0.25

# 10 Report Dimensions (weights sum to 1.0; missing dimensions excluded & weights renormalized)
DIMENSION_CONFIG = {
    "Technical Accuracy": {
        "weight": 0.16,
        "criteria": ["technical_accuracy", "correctness"],
        "is_delivery": False,
        "critical": True,
    },
    "Technical Depth": {
        "weight": 0.14,
        "criteria": ["technical_depth", "tradeoffs", "architecture"],
        "is_delivery": False,
        "critical": True,
    },
    "Problem Solving": {
        "weight": 0.14,
        "criteria": ["problem_solving", "edge_cases", "algorithmic_thinking"],
        "is_delivery": False,
        "critical": True,
    },
    "Communication Clarity": {
        "weight": 0.10,
        "criteria": ["clarity", "explanation_clarity"],
        "is_delivery": True,
        "critical": False,
    },
    "Structure & Organization": {
        "weight": 0.10,
        "criteria": ["structure", "star_structure"],
        "is_delivery": False,
        "critical": False,
    },
    "Role Relevance": {
        "weight": 0.10,
        "criteria": ["role_relevance", "domain_fit"],
        "is_delivery": False,
        "critical": False,
    },
    "Examples & Evidence": {
        "weight": 0.08,
        "criteria": ["examples", "concrete_metrics"],
        "is_delivery": False,
        "critical": False,
    },
    "Confidence & Delivery": {
        "weight": 0.06,
        "criteria": ["delivery_confidence", "pacing"],
        "is_delivery": True,
        "critical": False,
    },
    "Conciseness": {
        "weight": 0.06,
        "criteria": ["conciseness", "fluency"],
        "is_delivery": True,
        "critical": False,
    },
    "Professionalism": {
        "weight": 0.06,
        "criteria": ["professionalism", "ownership"],
        "is_delivery": False,
        "critical": False,
    },
}

# Grade bands on normalized 0.0 - 1.0 scale
GRADE_BANDS = [
    ("A", 0.85, "Outstanding", "#00e5c3"),
    ("B", 0.70, "Strong", "#00b8ff"),
    ("C", 0.55, "Competent", "#f59e0b"),
    ("D", 0.40, "Developing", "#f97316"),
    ("F", 0.00, "Below Bar", "#ef4444"),
]

# Report statuses (Operating Rule R2)
REPORT_STATUS_EVALUATED = "EVALUATED"
REPORT_STATUS_PARTIAL = "PARTIAL"
REPORT_STATUS_INCOMPLETE = "INCOMPLETE_INSUFFICIENT_DATA"
REPORT_STATUS_FAILED = "EVALUATION_FAILED"

# ── Phase 7: Reliability, Speed & Cost Configuration ─────────────────────────
FAST_GRADER_MODEL = "gemini-3.8-flash"
STRONG_GRADER_MODEL = "gemini-2.5-pro"
FALLBACK_GRADER_MODEL = "gemini-3.5-flash"
GEMINI_REQUEST_TIMEOUT_S = 15.0
MAX_EVAL_CONCURRENCY = 4
GRADER_MAX_OUTPUT_TOKENS = 650
RESUME_SUMMARY_MAX_CHARS = 350
DAILY_USER_TOKEN_BUDGET = 120000
BACKOFF_BASE_SECONDS = 0.25
BACKOFF_MAX_RETRIES = 3

