"""
Intent Handler for Ava AI Interviewer.
Deterministic dispatcher routing candidate intents to state transitions,
spoken responses, timer controls, and evidence tracking.
"""

from typing import Dict, Any, Tuple, Optional

from services.intent_classifier import (
    INTENT_ANSWER,
    INTENT_PARTIAL_ANSWER,
    INTENT_DONT_KNOW,
    INTENT_CLARIFICATION_REQUEST,
    INTENT_REPEAT_REQUEST,
    INTENT_REPHRASE_REQUEST,
    INTENT_HINT_REQUEST,
    INTENT_SKIP_REQUEST,
    INTENT_PAUSE_REQUEST,
    INTENT_RESUME_REQUEST,
    INTENT_END_INTERVIEW_REQUEST,
    INTENT_SMALL_TALK,
    INTENT_QUESTION_TO_INTERVIEWER,
    INTENT_OFF_TOPIC,
    INTENT_DISTRESS,
    INTENT_META_COMPLAINT,
    INTENT_STT_NOISE,
    INTENT_PROMPT_INJECTION
)
from services.interview_state_machine import (
    InterviewStateMachine,
    STATE_MAIN_QUESTIONING,
    STATE_PAUSED,
    STATE_END_REQUESTED,
    STATE_CLOSING,
    STATE_ENDED
)


class IntentHandler:
    """Dispatches conversational intents to deterministic state and dialogue actions."""

    @classmethod
    def handle_intent(
        cls,
        intent_data: Dict[str, Any],
        current_question: str,
        question_index: int,
        session_context: Dict[str, Any],
        hints_used_on_current_q: int = 0
    ) -> Dict[str, Any]:
        """
        Executes intent logic. Returns structured response with spoken message,
        action directives, state transition, and scoring flags.
        """
        intent = intent_data.get("intent", INTENT_ANSWER)
        candidate = session_context.get("candidate", {})
        c_name = candidate.get("first_name", "there")
        personality = session_context.get("personality", {})
        p_id = personality.get("id", "professional")

        # 1. End Interview Request
        if intent == INTENT_END_INTERVIEW_REQUEST:
            is_early = question_index < 3
            if is_early:
                closing_msg = (
                    f"Understood, {c_name}. We'll wrap up the interview here. "
                    "Since we only completed a couple of questions, your resulting feedback "
                    "report will be marked as Provisional based on limited observations."
                )
            else:
                closing_msg = (
                    f"Understood, {c_name}. Thank you for your time today. "
                    "We will conclude the interview here and compile your comprehensive evaluation report."
                )

            return {
                "action": "END_INTERVIEW",
                "done": True,
                "message": closing_msg,
                "audio_cutoff": True,  # Critical flag: halts all TTS playback immediately
                "is_scored": False,
                "target_state": STATE_ENDED,
                "advance_question": False,
                "trigger_report": True
            }

        # 2. Repeat Request
        if intent == INTENT_REPEAT_REQUEST:
            if p_id == "strict":
                repeat_msg = f"Repeating: {current_question}"
            elif p_id == "friendly":
                repeat_msg = f"Of course, {c_name}! Let me repeat that for you: {current_question}"
            else:
                repeat_msg = f"Certainly. Let me repeat the question: {current_question}"

            return {
                "action": "REPEAT_QUESTION",
                "done": False,
                "message": repeat_msg,
                "is_scored": False,
                "repeat_question": current_question,
                "advance_question": False
            }

        # 3. Rephrase Request
        if intent == INTENT_REPHRASE_REQUEST:
            rephrase_msg = (
                f"Sure, let me rephrase: In simpler terms, {current_question}"
            )
            return {
                "action": "REPHRASE_QUESTION",
                "done": False,
                "message": rephrase_msg,
                "is_scored": False,
                "advance_question": False
            }

        # 4. Hint Request
        if intent == INTENT_HINT_REQUEST:
            max_hints = personality.get("max_hints_per_question", 2)
            if hints_used_on_current_q >= max_hints:
                return {
                    "action": "HINT_LIMIT_REACHED",
                    "done": False,
                    "message": (
                        f"You've used all available hints for this question. "
                        "Give it your best attempt, or we can skip to the next question if you prefer."
                    ),
                    "is_scored": False,
                    "advance_question": False
                }

            sample_hints = personality.get("sample_lines", {}).get("hinting", [])
            hint_body = sample_hints[0] if sample_hints else "Think about the data structures and boundary constraints."
            return {
                "action": "PROVIDE_HINT",
                "done": False,
                "message": f"Here is a directional hint: {hint_body}",
                "is_scored": False,
                "hint_delivered": hint_body,
                "hints_used_count": hints_used_on_current_q + 1,
                "advance_question": False
            }

        # 5. Skip Request
        if intent == INTENT_SKIP_REQUEST:
            return {
                "action": "SKIP_QUESTION",
                "done": False,
                "message": f"No problem at all, {c_name}. We'll move on to the next question.",
                "is_scored": False,
                "question_skipped": True,
                "advance_question": True
            }

        # 6. Pause / Resume Request
        if intent == INTENT_PAUSE_REQUEST:
            return {
                "action": "PAUSE_INTERVIEW",
                "done": False,
                "message": f"Interview paused. Take your time, {c_name}. Say 'resume' or click Resume when you're ready.",
                "target_state": STATE_PAUSED,
                "is_scored": False,
                "advance_question": False
            }

        if intent == INTENT_RESUME_REQUEST:
            return {
                "action": "RESUME_INTERVIEW",
                "done": False,
                "message": f"Welcome back, {c_name}! Let's pick back up with our question: {current_question}",
                "target_state": STATE_MAIN_QUESTIONING,
                "is_scored": False,
                "advance_question": False
            }

        # 7. Don't Know / Blank
        if intent == INTENT_DONT_KNOW:
            if p_id == "friendly":
                dont_know_msg = (
                    f"That's completely okay, {c_name}! It's totally fine not to know every area. "
                    "Would you like a small hint to try it, or shall we move on to the next question?"
                )
            elif p_id == "strict":
                dont_know_msg = "Noted. We will proceed to the next question."
            else:
                dont_know_msg = (
                    "Understood. If you'd like a hint, let me know; otherwise we can proceed to the next question."
                )

            return {
                "action": "ACKNOWLEDGE_DONT_KNOW",
                "done": False,
                "message": dont_know_msg,
                "is_scored": False,
                "advance_question": (p_id == "strict")
            }

        # 8. Small Talk / Rapport
        if intent == INTENT_SMALL_TALK:
            if p_id == "friendly":
                small_talk_msg = (
                    f"I'm doing great, thank you so much for asking, {c_name}! "
                    f"I'm really enjoying our conversation. Let's return to our question: {current_question}"
                )
            elif p_id == "strict":
                small_talk_msg = f"I am ready. Proceeding with the question: {current_question}"
            else:
                small_talk_msg = (
                    f"I am doing well, thank you. Let's refocus on the question: {current_question}"
                )

            return {
                "action": "SMALL_TALK_REDIRECT",
                "done": False,
                "message": small_talk_msg,
                "is_scored": False,  # MUST NEVER BE SCORED
                "advance_question": False
            }

        # 9. Question to Interviewer (Process)
        if intent == INTENT_QUESTION_TO_INTERVIEWER:
            return {
                "action": "PROCESS_INQUIRY",
                "done": False,
                "message": (
                    "I conduct the interview rounds and evaluate your technical responses against objective rubrics. "
                    "Your full feedback report will be ready immediately after we finish. "
                    f"Let's continue with our question: {current_question}"
                ),
                "is_scored": False,
                "advance_question": False
            }

        # 10. Distress / Anxiety
        if intent == INTENT_DISTRESS:
            return {
                "action": "DISTRESS_SUPPORT",
                "done": False,
                "message": (
                    f"Take a deep breath, {c_name}. There is zero pressure here—this is purely a practice environment "
                    "to help you build confidence. We can pause for a few minutes, take a break, or end the session "
                    "whenever you feel like it. What would you like to do?"
                ),
                "is_scored": False,
                "target_state": STATE_PAUSED,
                "advance_question": False
            }

        # 11. Prompt Injection Attempt
        if intent == INTENT_PROMPT_INJECTION:
            return {
                "action": "REFUSE_INJECTION",
                "done": False,
                "message": (
                    "I evaluate answers strictly against objective technical rubrics and verified criteria. "
                    f"Please provide your engineering response to the question: {current_question}"
                ),
                "is_scored": False,
                "injection_blocked": True,
                "advance_question": False
            }

        # 12. STT Noise
        if intent == INTENT_STT_NOISE:
            return {
                "action": "STT_NOISE_IGNORED",
                "done": False,
                "message": "I didn't quite catch that. Please speak or type your answer whenever you're ready.",
                "is_scored": False,
                "advance_question": False
            }

        # Default: Process as regular technical answer
        return {
            "action": "EVALUATE_ANSWER",
            "done": False,
            "is_scored": True,
            "advance_question": True
        }

