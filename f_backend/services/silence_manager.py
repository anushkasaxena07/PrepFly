"""
Silence and Voice Behavior Manager for Ava AI Interviewer.
Coordinates deterministic 4-level silence escalation ladders,
interruption/barge-in ducking, and latency profiling.
"""

from typing import Dict, Any, List, Tuple, Optional
import time

SILENCE_LEVEL_0_THINKING = 0
SILENCE_LEVEL_1_CHECK_IN = 1
SILENCE_LEVEL_2_OFFER_HELP = 2
SILENCE_LEVEL_3_OFFER_SKIP = 3
SILENCE_LEVEL_4_PAUSE_OR_ABANDON = 4

# Base silence durations in seconds (Level 1, Level 2, Level 3, Level 4)
# Scaled by personality.silence_patience_s
DEFAULT_SILENCE_LADDER_FRIENDLY = {
    "level_1_s": 18,   # Gentle check-in
    "level_2_s": 32,   # Offer hint / collaborate
    "level_3_s": 48,   # Offer to move on
    "level_4_s": 65    # Presence check & pause
}

DEFAULT_SILENCE_LADDER_STRICT = {
    "level_1_s": 8,    # Direct prompt
    "level_2_s": 15,   # Clarifying specification
    "level_3_s": 22,   # Advance specification
    "level_4_s": 30    # Pause / auto-record blank
}

DEFAULT_SILENCE_LADDER_PROFESSIONAL = {
    "level_1_s": 14,
    "level_2_s": 26,
    "level_3_s": 40,
    "level_4_s": 55
}


class SilenceManager:
    """Deterministic manager for candidate silence escalation and turn-taking."""

    @classmethod
    def get_ladder_thresholds(cls, personality_id: str, track_id: str = "general") -> Dict[str, int]:
        """Calculates deterministic silence threshold seconds based on personality & track."""
        if personality_id == "strict":
            ladder = dict(DEFAULT_SILENCE_LADDER_STRICT)
        elif personality_id == "friendly":
            ladder = dict(DEFAULT_SILENCE_LADDER_FRIENDLY)
        else:
            ladder = dict(DEFAULT_SILENCE_LADDER_PROFESSIONAL)

        # Certain tracks (DSA, Logic Puzzles, System Design) require longer thinking pauses
        if track_id in ("dsa_algorithms", "logic_puzzles", "system_design"):
            ladder["level_1_s"] += 4
            ladder["level_2_s"] += 6
            ladder["level_3_s"] += 8
            ladder["level_4_s"] += 10

        return ladder

    @classmethod
    def evaluate_silence_state(
        cls,
        elapsed_silence_seconds: float,
        current_level_fired: int,
        personality_id: str,
        track_id: str = "general",
        candidate_name: str = "Candidate"
    ) -> Tuple[int, Optional[Dict[str, Any]]]:
        """
        Evaluates elapsed candidate silence against the personality ladder.
        Each escalation level fires at most once.
        Returns (new_level, action_dict_or_none).
        """
        thresholds = cls.get_ladder_thresholds(personality_id, track_id)

        # Level 4: Max silence exceeded -> Auto-Pause / Presence check
        if elapsed_silence_seconds >= thresholds["level_4_s"] and current_level_fired < SILENCE_LEVEL_4_PAUSE_OR_ABANDON:
            if personality_id == "strict":
                msg = f"{candidate_name}, no response detected. Pausing session."
            else:
                msg = f"{candidate_name}, are you still there? I'm going to pause the interview for you. Click Resume whenever you're ready to continue."

            return SILENCE_LEVEL_4_PAUSE_OR_ABANDON, {
                "level": SILENCE_LEVEL_4_PAUSE_OR_ABANDON,
                "action": "AUTO_PAUSE",
                "message": msg,
                "target_state": "PAUSED",
                "audio_cutoff": False
            }

        # Level 3: Offer to skip/move on
        if elapsed_silence_seconds >= thresholds["level_3_s"] and current_level_fired < SILENCE_LEVEL_3_OFFER_SKIP:
            if personality_id == "strict":
                msg = "No response. We can move to the next question if you wish."
            elif personality_id == "friendly":
                msg = "No problem at all! We can come back to this later. Shall we move to the next question?"
            else:
                msg = "We can pass on this question and proceed to the next topic if you prefer."

            return SILENCE_LEVEL_3_OFFER_SKIP, {
                "level": SILENCE_LEVEL_3_OFFER_SKIP,
                "action": "OFFER_SKIP",
                "message": msg,
                "target_state": "MAIN_QUESTIONING"
            }

        # Level 2: Offer hint / collaborative nudge
        if elapsed_silence_seconds >= thresholds["level_2_s"] and current_level_fired < SILENCE_LEVEL_2_OFFER_HELP:
            if personality_id == "strict":
                msg = "State your current parameter analysis or ask for a clarification."
            elif personality_id == "friendly":
                msg = "Would you like a little hint, or should we talk through the first step together?"
            else:
                msg = "If you'd like a directional hint or clarification on constraints, feel free to ask."

            return SILENCE_LEVEL_2_OFFER_HELP, {
                "level": SILENCE_LEVEL_2_OFFER_HELP,
                "action": "OFFER_HINT",
                "message": msg,
                "target_state": "MAIN_QUESTIONING"
            }

        # Level 1: Gentle check-in
        if elapsed_silence_seconds >= thresholds["level_1_s"] and current_level_fired < SILENCE_LEVEL_1_CHECK_IN:
            if personality_id == "strict":
                msg = "Do you need the question repeated?"
            elif personality_id == "friendly":
                msg = f"Take your time, {candidate_name}. Would you like me to repeat the question?"
            else:
                msg = "Take your time. Let me know if you would like me to repeat or rephrase the question."

            return SILENCE_LEVEL_1_CHECK_IN, {
                "level": SILENCE_LEVEL_1_CHECK_IN,
                "action": "CHECK_IN",
                "message": msg,
                "target_state": "MAIN_QUESTIONING"
            }

        # Level 0: Normal thinking time
        return current_level_fired, None

    @classmethod
    def handle_barge_in(cls, is_ava_talking: bool) -> Dict[str, Any]:
        """
        Executes immediate audio ducking when candidate speaks while Ava is talking.
        Returns immediate instruction to stop TTS audio and switch to LISTENING.
        """
        return {
            "barge_in_detected": True,
            "cancel_tts": True,
            "target_substate": "LISTENING",
            "message": "Candidate interrupted Ava; audio canceled immediately."
        }

