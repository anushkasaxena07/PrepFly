"""
Intent Classifier for Ava AI Interviewer.
High-precision multi-intent detection using deterministic regex fast-paths,
fuzzy matching for typos/STT noise, and structured LLM classification.
Covers 16+ conversational intents with confidence scores and safety flags.
"""

import re
from typing import Dict, Any, List, Tuple, Optional

INTENT_ANSWER = "answer"
INTENT_PARTIAL_ANSWER = "partial_answer"
INTENT_DONT_KNOW = "dont_know"
INTENT_CLARIFICATION_REQUEST = "clarification_request"
INTENT_REPEAT_REQUEST = "repeat_request"
INTENT_REPHRASE_REQUEST = "rephrase_request"
INTENT_HINT_REQUEST = "hint_request"
INTENT_SKIP_REQUEST = "skip_request"
INTENT_PAUSE_REQUEST = "pause_request"
INTENT_RESUME_REQUEST = "resume_request"
INTENT_END_INTERVIEW_REQUEST = "end_interview_request"
INTENT_SMALL_TALK = "small_talk"
INTENT_QUESTION_TO_INTERVIEWER = "question_to_interviewer"
INTENT_OFF_TOPIC = "off_topic"
INTENT_DISTRESS = "distress"
INTENT_META_COMPLAINT = "meta_complaint"
INTENT_STT_NOISE = "stt_noise"
INTENT_PROMPT_INJECTION = "prompt_injection"

# Fast-path compiled patterns (ordered by evaluation priority)
REGEX_INTENT_PATTERNS: List[Tuple[str, List[str]]] = [
    # 1. Prompt Injections & Jailbreaks
    (INTENT_PROMPT_INJECTION, [
        r'\b(?:ignore\s+(?:all\s+)?(?:previous\s+)?instructions|system\s+prompt|give\s+me\s+(?:full\s+|100%?\s+|perfect\s+)marks|bypass\s+evaluation|you\s+are\s+now\s+a\s+different\b|jailbreak|disregard\s+the\s+rubric)\b',
        r'\b(?:override\s+scoring|output\s+(?:only\s+)?json\s+saying\s+passed|act\s+as\s+an\s+unrestricted)\b'
    ]),

    # 2. End / Exit Request (High Priority)
    (INTENT_END_INTERVIEW_REQUEST, [
        r'\b(?:end\s+(?:the\s+)?(?:interview|inw|call|session)|stop\s+(?:the\s+)?(?:interview|inw|call|session))\b',
        r'\b(?:i\s+(?:want\s+to|wanna|would\s+like\s+to)\s+(?:end|stop|quit|finish|exit|terminate))\b',
        r'\b(?:let\'?s\s+(?:end|stop|finish|wrap\s+up)(?:\s+here|\s+now)?)\b',
        r'\b(?:i\s+am\s+done|i\'?m\s+done(?:\s+with\s+the\s+interview)?|that\'?s\s+all(?:\s+from\s+me)?|can\s+we\s+finish|can\s+we\s+stop)\b',
        r'\b(?:wrap\s+up\s+early|finish\s+the\s+interview|exit\s+interview|close\s+the\s+interview)\b',
        r'\b(?:khatam\s+karo|band\s+karo|ruk\s+jao|bas\s+itna\s+hi)\b'  # Hinglish / Indian candidate common expressions
    ]),

    # 3. Distress / Anxiety
    (INTENT_DISTRESS, [
        r'\b(?:i\s+can\'?t\s+do\s+this|having\s+(?:a\s+)?panic\s+attack|too\s+stressed|feeling\s+(?:very\s+)?anxious|i\'?m\s+freaking\s+out|overwhelmed|need\s+a\s+break\s+badly)\b'
    ]),

    # 4. Repeat Request
    (INTENT_REPEAT_REQUEST, [
        r'\b(?:repeat(?:\s+the\s+question)?|pardon(?:\s+me)?|say\s+that\s+again|say\s+again|didn\'?t\s+hear(?:\s+you)?|come\s+again)\b',
        r'\b(?:could\s+you\s+repeat|can\s+you\s+repeat|please\s+repeat|repeat\s+please)\b'
    ]),

    # 5. Rephrase Request
    (INTENT_REPHRASE_REQUEST, [
        r'\b(?:rephrase(?:\s+the\s+question)?|can\s+you\s+rephrase|say\s+it\s+differently|explain\s+differently|in\s+other\s+words|didn\'?t\s+understand\s+the\s+question)\b'
    ]),

    # 6. Hint Request
    (INTENT_HINT_REQUEST, [
        r'\b(?:(?:give|need|want|can\s+i\s+get|can\s+you\s+give)\s+(?:me\s+)?(?:a\s+)?hint|give\s+a\s+hint|small\s+hint|little\s+hint|nudge)\b',
        r'\b(?:stuck|any\s+clue|direction\s+please|point\s+me\s+in\s+the\s+right\s+direction)\b'
    ]),

    # 7. Skip Request
    (INTENT_SKIP_REQUEST, [
        r'\b(?:skip(?:\s+this(?:\s+question)?)?|pass(?:\s+on\s+this)?|next\s+question\s+please|can\s+we\s+skip|move\s+to\s+next\s+question)\b'
    ]),

    # 8. Pause / Resume Request
    (INTENT_PAUSE_REQUEST, [
        r'\b(?:pause(?:\s+the\s+interview)?|give\s+me\s+a\s+(?:moment|second|sec|minute)|one\s+second|wait\s+a\s+(?:sec|second|moment)|can\s+i\s+pause|hold\s+on(?:\s+a\s+second)?)\b'
    ]),
    (INTENT_RESUME_REQUEST, [
        r'\b(?:resume(?:\s+the\s+interview)?|i\'?m\s+back|ready\s+to\s+continue|let\'?s\s+continue|continue\s+please|ready\s+now)\b'
    ]),

    # 9. I Don't Know / Blank
    (INTENT_DONT_KNOW, [
        r'\b(?:i\s+don\'?t\s+know|no\s+idea|i\s+have\s+no\s+idea|i\'?m\s+drawing\s+a\s+blank|not\s+sure\s+about\s+this|not\s+familiar\s+with\s+this)\b',
        r'\b(?:haven\'?t\s+worked\s+with\s+this|never\s+heard\s+of\s+this|pata\s+nahi|nahi\s+pata)\b'
    ]),

    # 10. Clarification Request
    (INTENT_CLARIFICATION_REQUEST, [
        r'\b(?:what\s+do\s+you\s+mean\s+by|(?:can|could)\s+you\s+(?:please\s+)?clarify|could\s+you\s+explain\s+what\s+you\s+mean|are\s+you\s+asking\s+about|do\s+you\s+mean|clarify\s+(?:what|the))\b'
    ]),

    # 11. Small Talk / Rapport
    (INTENT_SMALL_TALK, [
        r'\b(?:how\s+are\s+you|how\'?s\s+it\s+going|how\s+is\s+your\s+day|good\s+morning|good\s+afternoon|good\s+evening|nice\s+to\s+meet\s+you|pleasure\s+to\s+meet\s+you|hello\s+ava|hi\s+ava)\b',
        r'\b(?:are\s+you\s+a\s+real\s+person|are\s+you\s+human|who\s+made\s+you|what\s+is\s+your\s+name)\b',
        r'\b(?:i\'?m\s+(?:doing\s+)?(?:great|good|fine|well)|doing\s+(?:great|good|fine|well)|excited\s+to\s+(?:be\s+here|interview))\b'
    ]),

    # 12. Question to Interviewer (Process)
    (INTENT_QUESTION_TO_INTERVIEWER, [
        r'\b(?:how\s+many\s+questions(?:\s+are\s+left)?|how\s+much\s+time(?:\s+is\s+left)?|how\s+am\s+i\s+doing|what\s+is\s+my\s+score|what\s+company\s+is\s+this)\b'
    ]),

    # 13. Meta Complaint
    (INTENT_META_COMPLAINT, [
        r'\b(?:this\s+is\s+too\s+hard|questions\s+are\s+unfair|this\s+makes\s+no\s+sense|the\s+mic\s+isn\'?t\s+working|can\s+you\s+hear\s+me)\b'
    ])
]


class IntentClassifier:
    """Classifies candidate utterances into structured conversational intents."""

    @classmethod
    def classify_intent(cls, utterance: str) -> Dict[str, Any]:
        """
        Classifies candidate utterance using deterministic fast-path patterns,
        fuzzy typo tolerance, and word-length heuristics.
        Returns {intent, confidence, is_actionable, raw_utterance}.
        """
        if not utterance or not utterance.strip():
            return {
                "intent": INTENT_STT_NOISE,
                "confidence": 1.0,
                "is_actionable": False,
                "raw_utterance": ""
            }

        cleaned = utterance.strip().lower()
        words = re.findall(r'\b[a-z0-9\']+\b', cleaned)
        word_count = len(words)

        # Check for pure STT noise (single random syllables or punctuation)
        if (word_count == 0 and not re.search(r'[a-zA-Z0-9]', cleaned)) or (word_count <= 1 and cleaned in {"um", "uh", "ah", "er", ".", "...", "?", "hmm"}):
            return {
                "intent": INTENT_STT_NOISE,
                "confidence": 0.95,
                "is_actionable": False,
                "raw_utterance": utterance
            }

        # 1. High-priority deterministic pattern matching
        for intent_name, patterns in REGEX_INTENT_PATTERNS:
            for pat in patterns:
                if re.search(pat, cleaned):
                    # Guard: If candidate gave a substantial technical answer (> 20 words)
                    # that simply happens to use the word "repeat" or "hint" in technical prose,
                    # treat as regular technical answer!
                    if intent_name in (INTENT_REPEAT_REQUEST, INTENT_HINT_REQUEST, INTENT_PAUSE_REQUEST, INTENT_CLARIFICATION_REQUEST):
                        if word_count > 25:
                            continue

                    # Injections and End requests always take precedence regardless of length
                    confidence = 0.98 if intent_name in (INTENT_PROMPT_INJECTION, INTENT_END_INTERVIEW_REQUEST) else 0.90
                    return {
                        "intent": intent_name,
                        "confidence": confidence,
                        "is_actionable": True,
                        "matched_pattern": pat,
                        "raw_utterance": utterance
                    }

        # 2. Typo-tolerant fast matching for end requests ("end inw", "stop inw", "quitt", "end now")
        end_typos = {"end inw", "stop inw", "end intrview", "stop intrvw", "i wanna quit", "done with inw"}
        if any(typo in cleaned for typo in end_typos) or cleaned in {"end", "quit", "exit", "stop", "finish"}:
            return {
                "intent": INTENT_END_INTERVIEW_REQUEST,
                "confidence": 0.92,
                "is_actionable": True,
                "matched_pattern": "typo_fuzzy_match",
                "raw_utterance": utterance
            }

        # 3. Partial answer vs full answer heuristic
        if word_count < 10:
            return {
                "intent": INTENT_PARTIAL_ANSWER,
                "confidence": 0.75,
                "is_actionable": False,
                "raw_utterance": utterance
            }

        # Default: Full technical answer
        return {
            "intent": INTENT_ANSWER,
            "confidence": 0.90,
            "is_actionable": False,
            "raw_utterance": utterance
        }
