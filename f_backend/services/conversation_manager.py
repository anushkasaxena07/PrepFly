"""
Conversation Manager for Ava AI Interviewer.
Coordinates personality-aware greetings, format briefing, rolling memory,
deterministic follow-up policies, active-listening probing, callbacks, and graceful wrap-up.
"""

import re
import hashlib
from typing import Dict, Any, List, Tuple, Optional

# Follow-up moves
MOVE_ACKNOWLEDGE_AND_NEXT = "acknowledge_and_next"
MOVE_PROBE_DETAIL = "probe_detail"
MOVE_CHALLENGE = "challenge"
MOVE_CLARIFY_REQUIREMENT = "clarify_requirement"
MOVE_GIVE_HINT = "give_hint"
MOVE_REDIRECT_TO_TOPIC = "redirect_to_topic"
MOVE_SUMMARIZE_AND_TRANSITION = "summarize_and_transition"

# Natural opening connectors per personality
TRANSITION_PHRASES: Dict[str, List[str]] = {
    "friendly": [
        "That's really interesting. Building on what you said,",
        "I love that perspective. Let's explore that a bit deeper:",
        "That makes complete sense. Shifting our lens slightly,",
        "Really thoughtful explanation! Now thinking about,",
        "Thanks for walking through that. Turning to another aspect,"
    ],
    "professional": [
        "Understood. Moving forward to the next consideration,",
        "Noted. With that architecture in place,",
        "That provides clear context. Now let's examine,",
        "Understood. Looking at the operational side,",
        "Thank you for clarifying. Shifting our focus to,"
    ],
    "challenging": [
        "I see that design choice. Now let's analyze where it fails:",
        "Understood, but that assumes optimal conditions. Consider:",
        "Right, but what happens when latency spikes? Specifically,",
        "Let's stress-test that assumption. What if,",
        "Interesting hypothesis. However, in the worst-case scenario,"
    ],
    "strict": [
        "Noted. Next specification:",
        "Recorded. Proceeding to the boundary constraint:",
        "Understood. Define the following:",
        "Recorded. Analyze this parameter:"
    ],
    "senior_engineer": [
        "Yeah, that's a classic engineering trade-off. Looking at production scale,",
        "Fair point. Now from an on-call and blast-radius perspective,",
        "I like that pragmatic call. Thinking about long-term maintainability,",
        "Makes sense for V1. As traffic scales 10x though,",
        "Right. Looking at the operational complexity,"
    ]
}


class ConversationManager:
    """Manages conversational dialogue, active listening, and rolling memory."""

    @classmethod
    def initialize_rolling_memory(cls) -> Dict[str, Any]:
        """Creates a fresh, structured rolling memory ledger."""
        return {
            "topics_covered": [],
            "claims_made": [],
            "inconsistencies": [],
            "strengths_noted": [],
            "weaknesses_noted": [],
            "hints_given_count": 0,
            "stem_hashes_asked": [],
            "callbacks_available": [],
            "recent_openers": []
        }

    @classmethod
    def generate_opening_turn(cls, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates Turn 1: Personality-calibrated greeting, rapport building, and format briefing.
        Strict interviews have brief greetings; Friendly interviews have 2 rapport turns.
        Rapport turns are tagged is_scored = False.
        """
        candidate = session_context["candidate"]
        track = session_context["track"]
        personality = session_context["personality"]
        c_name = candidate["first_name"] or candidate["display_name"]
        role = candidate["target_role"]
        duration = session_context["constraints"]["time_budget_minutes"]

        # Select personality greeting
        sample_greetings = personality.get("sample_lines", {}).get("greeting", [])
        if sample_greetings:
            raw_greet = sample_greetings[0].replace("{name}", c_name)
        else:
            raw_greet = f"Hello {c_name}, I'm Ava. Welcome to your {track['display_name']} interview."

        # Format briefing component
        format_briefing = (
            f"Today's round is focused on {track['display_name']} and will take approximately {duration} minutes. "
            f"{track['opening_scope_sentence']} "
            f"Feel free to think aloud as you reason through problems. If you need a question repeated, "
            f"want a small hint, or wish to pause or end early, just let me know."
        )

        if personality["id"] == "strict":
            # Strict mode: brief and straight to business
            opening_message = f"{raw_greet} {track['opening_scope_sentence']}"
        elif personality["id"] == "friendly":
            # Friendly mode: warm icebreaker
            opening_message = (
                f"{raw_greet} Before we begin our {track['display_name']} questions, "
                f"how are you feeling today and how is your day going so far?"
            )
        else:
            # Professional / Senior Staff / Challenging: greeting + format briefing
            opening_message = f"{raw_greet}\n\n{format_briefing}"

        return {
            "turn_number": 1,
            "turn_type": "GREETING_AND_ICEBREAKER",
            "is_scored": False,
            "message": opening_message,
            "stage": "Greeting & Format Briefing",
            "needs_candidate_response": True,
            "current_state": "GREETING"
        }

    @classmethod
    def evaluate_followup_decision(
        cls,
        last_answer: str,
        normalized_score: float,
        current_question_followups: int,
        session_context: Dict[str, Any],
        rolling_memory: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Deterministic policy choosing the interviewer's next move.
        Considers candidate's answer score, length, ambiguity, and personality limits.
        """
        personality = session_context["personality"]
        max_followups = personality.get("followup_depth", 2)
        challenge_rate = personality.get("challenge_rate", 0.40)

        ans_words = last_answer.strip().split()
        word_count = len(ans_words)

        # 1. Candidate provided very short or vague answer (< 12 words)
        if word_count < 12 and current_question_followups < max_followups:
            return MOVE_PROBE_DETAIL, {
                "reason": "candidate_answer_concise_or_incomplete",
                "target_depth": current_question_followups + 1
            }

        # 2. Candidate answer contains significant technical weakness (score < 0.45)
        if normalized_score < 0.45 and current_question_followups < max_followups:
            # If challenging personality or challenge threshold triggered
            if challenge_rate >= 0.50:
                return MOVE_CHALLENGE, {
                    "reason": "weak_claim_stress_test",
                    "target_depth": current_question_followups + 1
                }
            else:
                return MOVE_CLARIFY_REQUIREMENT, {
                    "reason": "gentle_clarification_on_missing_requirement",
                    "target_depth": current_question_followups + 1
                }

        # 3. Candidate made a strong claim (> 25 words, score >= 0.75) and personality allows deep follow-ups
        if normalized_score >= 0.75 and current_question_followups < max_followups:
            if personality["id"] in ("challenging", "senior_engineer"):
                return MOVE_CHALLENGE, {
                    "reason": "scale_or_boundary_stress_test",
                    "target_depth": current_question_followups + 1
                }

        # 4. Otherwise, advance to next question
        return MOVE_ACKNOWLEDGE_AND_NEXT, {
            "reason": "max_followups_reached_or_satisfactory_answer",
            "target_depth": 0
        }

    @classmethod
    def update_rolling_memory(
        cls,
        memory: Dict[str, Any],
        turn_number: int,
        question_text: str,
        candidate_response: str,
        skill_id: Optional[str] = None,
        score: float = 0.0
    ) -> Dict[str, Any]:
        """Updates rolling memory with newly observed claims, skills, and stem hashes."""
        updated = dict(memory)

        # Record stem hash for anti-repetition
        stem_h = hashlib.sha256(question_text.strip().lower().encode("utf-8")).hexdigest()[:12]
        stems = list(updated.get("stem_hashes_asked", []))
        if stem_h not in stems:
            stems.append(stem_h)
        updated["stem_hashes_asked"] = stems

        # Record topic / skill
        if skill_id:
            topics = list(updated.get("topics_covered", []))
            if skill_id not in topics:
                topics.append(skill_id)
            updated["topics_covered"] = topics

        # Extract concrete candidate phrase for future callbacks (extract 6-12 word phrase)
        words = candidate_response.strip().split()
        if len(words) >= 6:
            snippet = " ".join(words[:8])
            callbacks = list(updated.get("callbacks_available", []))
            callbacks.append({
                "snippet": snippet,
                "turn_number": turn_number,
                "skill_id": skill_id
            })
            updated["callbacks_available"] = callbacks[-5:]  # Retain top 5 recent callbacks

        # Track strengths / weaknesses
        if score >= 0.80 and skill_id:
            strengths = list(updated.get("strengths_noted", []))
            strengths.append(skill_id)
            updated["strengths_noted"] = list(set(strengths))
        elif score < 0.40 and skill_id:
            weaknesses = list(updated.get("weaknesses_noted", []))
            weaknesses.append(skill_id)
            updated["weaknesses_noted"] = list(set(weaknesses))

        return updated

    @classmethod
    def format_callback_reference(cls, rolling_memory: Dict[str, Any]) -> Optional[str]:
        """Pulls an earlier candidate statement for natural dialogue callbacks."""
        callbacks = rolling_memory.get("callbacks_available", [])
        if callbacks and len(callbacks) >= 2:
            earlier = callbacks[0]
            return f"Earlier you mentioned \"{earlier['snippet']}...\";"
        return None

    @classmethod
    def generate_natural_transition(
        cls,
        personality_id: str,
        recent_openers: List[str]
    ) -> Tuple[str, List[str]]:
        """
        Selects a natural transitional phrase ensuring no repetition within the last 3 turns.
        """
        options = TRANSITION_PHRASES.get(personality_id, TRANSITION_PHRASES["professional"])
        filtered = [opt for opt in options if opt not in recent_openers]
        chosen = filtered[0] if filtered else options[0]

        updated_openers = list(recent_openers)
        updated_openers.append(chosen)
        return chosen, updated_openers[-3:]

    @classmethod
    def generate_closing_turn(
        cls,
        session_context: Dict[str, Any],
        scored_turns_count: int
    ) -> Dict[str, Any]:
        """Generates graceful closing dialogue matching personality."""
        candidate = session_context["candidate"]
        personality = session_context["personality"]
        c_name = candidate["first_name"] or candidate["display_name"]

        closings = personality.get("sample_lines", {}).get("closing", [])
        if closings:
            closing_speech = closings[0].replace("{name}", c_name)
        else:
            closing_speech = f"Thank you {c_name} for your time today. Your evaluation report is now being generated."

        # If too short to produce authoritative report:
        is_limited = scored_turns_count < 3
        if is_limited:
            closing_speech += (
                " Note that since we only completed a few questions, your resulting feedback "
                "report will be marked as Provisional based on limited observations."
            )

        return {
            "turn_type": "CLOSING",
            "is_scored": False,
            "message": closing_speech,
            "stage": "Closing & Evaluation",
            "is_provisional": is_limited,
            "total_scored_turns": scored_turns_count
        }

