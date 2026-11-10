"""
Interview State Machine: Deterministic pure state transitions for Ava AI Interviewer.
Manages lifecycle stages, main questioning substates, and interrupt states.
"""

from typing import Dict, Any, Tuple, Optional, Set

# Top-level lifecycle states
STATE_PRE_START = "PRE_START"
STATE_GREETING = "GREETING"
STATE_ICEBREAKER = "ICEBREAKER"
STATE_FORMAT_BRIEFING = "FORMAT_BRIEFING"
STATE_MAIN_QUESTIONING = "MAIN_QUESTIONING"
STATE_WRAP_UP_QUESTIONS = "WRAP_UP_QUESTIONS"
STATE_CLOSING = "CLOSING"
STATE_ENDED = "ENDED"

# Interrupt states
STATE_PAUSED = "PAUSED"
STATE_CLARIFICATION = "CLARIFICATION"
STATE_TECH_ISSUE = "TECH_ISSUE"
STATE_END_REQUESTED = "END_REQUESTED"

# Main questioning substates
SUBSTATE_ASKED = "ASKED"
SUBSTATE_LISTENING = "LISTENING"
SUBSTATE_PROBING = "PROBING"
SUBSTATE_HINTING = "HINTING"
SUBSTATE_EVALUATING_BG = "EVALUATING_BG"
SUBSTATE_TRANSITION = "TRANSITION"

ALL_PRIMARY_STATES: Set[str] = {
    STATE_PRE_START, STATE_GREETING, STATE_ICEBREAKER, STATE_FORMAT_BRIEFING,
    STATE_MAIN_QUESTIONING, STATE_WRAP_UP_QUESTIONS, STATE_CLOSING, STATE_ENDED,
    STATE_PAUSED, STATE_CLARIFICATION, STATE_TECH_ISSUE, STATE_END_REQUESTED
}

ALL_SUBSTATES: Set[str] = {
    SUBSTATE_ASKED, SUBSTATE_LISTENING, SUBSTATE_PROBING, SUBSTATE_HINTING,
    SUBSTATE_EVALUATING_BG, SUBSTATE_TRANSITION
}

# Legal transition graph: current_state -> set of legal target states
LEGAL_TRANSITIONS: Dict[str, Set[str]] = {
    STATE_PRE_START: {STATE_GREETING, STATE_TECH_ISSUE, STATE_END_REQUESTED},
    STATE_GREETING: {STATE_ICEBREAKER, STATE_FORMAT_BRIEFING, STATE_MAIN_QUESTIONING, STATE_PAUSED, STATE_END_REQUESTED, STATE_TECH_ISSUE},
    STATE_ICEBREAKER: {STATE_ICEBREAKER, STATE_FORMAT_BRIEFING, STATE_MAIN_QUESTIONING, STATE_PAUSED, STATE_END_REQUESTED, STATE_TECH_ISSUE},
    STATE_FORMAT_BRIEFING: {STATE_MAIN_QUESTIONING, STATE_CLARIFICATION, STATE_PAUSED, STATE_END_REQUESTED, STATE_TECH_ISSUE},
    STATE_MAIN_QUESTIONING: {STATE_MAIN_QUESTIONING, STATE_WRAP_UP_QUESTIONS, STATE_CLOSING, STATE_PAUSED, STATE_CLARIFICATION, STATE_END_REQUESTED, STATE_TECH_ISSUE},
    STATE_WRAP_UP_QUESTIONS: {STATE_WRAP_UP_QUESTIONS, STATE_CLOSING, STATE_PAUSED, STATE_END_REQUESTED, STATE_TECH_ISSUE},
    STATE_CLOSING: {STATE_ENDED, STATE_TECH_ISSUE},
    STATE_ENDED: set(),  # Terminal state

    # Interrupt states can transition back or terminate
    STATE_PAUSED: {STATE_GREETING, STATE_ICEBREAKER, STATE_FORMAT_BRIEFING, STATE_MAIN_QUESTIONING, STATE_WRAP_UP_QUESTIONS, STATE_END_REQUESTED, STATE_ENDED},
    STATE_CLARIFICATION: {STATE_FORMAT_BRIEFING, STATE_MAIN_QUESTIONING, STATE_PAUSED, STATE_END_REQUESTED},
    STATE_TECH_ISSUE: {STATE_PRE_START, STATE_GREETING, STATE_MAIN_QUESTIONING, STATE_PAUSED, STATE_END_REQUESTED, STATE_ENDED},
    STATE_END_REQUESTED: {STATE_MAIN_QUESTIONING, STATE_CLOSING, STATE_ENDED}
}

LEGAL_SUBSTATE_TRANSITIONS: Dict[str, Set[str]] = {
    SUBSTATE_ASKED: {SUBSTATE_LISTENING, SUBSTATE_HINTING},
    SUBSTATE_LISTENING: {SUBSTATE_EVALUATING_BG, SUBSTATE_PROBING, SUBSTATE_HINTING, SUBSTATE_TRANSITION},
    SUBSTATE_PROBING: {SUBSTATE_LISTENING, SUBSTATE_HINTING, SUBSTATE_TRANSITION},
    SUBSTATE_HINTING: {SUBSTATE_LISTENING, SUBSTATE_TRANSITION},
    SUBSTATE_EVALUATING_BG: {SUBSTATE_PROBING, SUBSTATE_TRANSITION, SUBSTATE_ASKED},
    SUBSTATE_TRANSITION: {SUBSTATE_ASKED}
}


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal state transition is attempted."""
    pass


class InterviewStateMachine:
    """Pure, deterministic state machine controller for interview sessions."""

    @classmethod
    def can_transition(cls, from_state: str, to_state: str) -> bool:
        """Checks if a transition between two primary states is legal."""
        if from_state not in LEGAL_TRANSITIONS:
            return False
        return to_state in LEGAL_TRANSITIONS[from_state]

    @classmethod
    def transition(
        cls,
        current_state: str,
        target_state: str,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates and executes a deterministic state transition.
        Returns (success, new_state, updated_metadata).
        """
        metadata = dict(session_metadata or {})

        if current_state == target_state:
            return True, current_state, metadata

        if not cls.can_transition(current_state, target_state):
            err_msg = (
                f"Illegal state transition from '{current_state}' to '{target_state}'. "
                f"Allowed target states: {sorted(list(LEGAL_TRANSITIONS.get(current_state, set())))}"
            )
            return False, current_state, {"error": err_msg}

        # Handle metadata state history
        history = list(metadata.get("state_history", []))
        history.append({
            "from_state": current_state,
            "to_state": target_state
        })
        metadata["state_history"] = history
        metadata["current_state"] = target_state

        return True, target_state, metadata

    @classmethod
    def can_transition_substate(cls, from_substate: str, to_substate: str) -> bool:
        """Checks if a questioning substate transition is legal."""
        if from_substate not in LEGAL_SUBSTATE_TRANSITIONS:
            return False
        return to_substate in LEGAL_SUBSTATE_TRANSITIONS[from_substate]

