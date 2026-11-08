"""
Interview State Service: Deterministic state machine, session turn tracking,
idempotency control, and session recovery for Ava AI interviews.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

# Valid state machine states
STATE_INITIALIZING = "INITIALIZING"
STATE_ASKING = "ASKING"
STATE_WAITING_FOR_RESPONSE = "WAITING_FOR_RESPONSE"
STATE_ANALYZING = "ANALYZING"
STATE_FOLLOW_UP = "FOLLOW_UP"
STATE_CLARIFICATION = "CLARIFICATION"
STATE_NEXT_QUESTION = "NEXT_QUESTION"
STATE_PAUSED = "PAUSED"
STATE_COMPLETED = "COMPLETED"
STATE_FAILED = "FAILED"

VALID_STATES = {
    STATE_INITIALIZING,
    STATE_ASKING,
    STATE_WAITING_FOR_RESPONSE,
    STATE_ANALYZING,
    STATE_FOLLOW_UP,
    STATE_CLARIFICATION,
    STATE_NEXT_QUESTION,
    STATE_PAUSED,
    STATE_COMPLETED,
    STATE_FAILED
}

# Permitted state transitions
PERMITTED_TRANSITIONS = {
    STATE_INITIALIZING: {STATE_ASKING, STATE_FAILED},
    STATE_ASKING: {STATE_WAITING_FOR_RESPONSE, STATE_PAUSED, STATE_FAILED},
    STATE_WAITING_FOR_RESPONSE: {STATE_ANALYZING, STATE_PAUSED, STATE_COMPLETED, STATE_FAILED},
    STATE_ANALYZING: {STATE_FOLLOW_UP, STATE_CLARIFICATION, STATE_NEXT_QUESTION, STATE_COMPLETED, STATE_FAILED},
    STATE_FOLLOW_UP: {STATE_WAITING_FOR_RESPONSE, STATE_PAUSED, STATE_FAILED},
    STATE_CLARIFICATION: {STATE_WAITING_FOR_RESPONSE, STATE_PAUSED, STATE_FAILED},
    STATE_NEXT_QUESTION: {STATE_WAITING_FOR_RESPONSE, STATE_COMPLETED, STATE_PAUSED, STATE_FAILED},
    STATE_PAUSED: {STATE_WAITING_FOR_RESPONSE, STATE_ASKING, STATE_COMPLETED, STATE_FAILED},
    STATE_COMPLETED: set(),  # Terminal state
    STATE_FAILED: {STATE_INITIALIZING, STATE_WAITING_FOR_RESPONSE}  # Retry
}


class InterviewStateService:
    """Manages interview lifecycle states, transition invariants, turn auditing, and idempotency."""

    @staticmethod
    def validate_transition(current_state: str, next_state: str) -> bool:
        """Verifies if transitioning from current_state to next_state is valid."""
        if current_state not in VALID_STATES or next_state not in VALID_STATES:
            return False
        return next_state in PERMITTED_TRANSITIONS.get(current_state, set())

    @staticmethod
    def get_session_state(supabase_client, session_id: str) -> Dict[str, Any]:
        """Fetches normalized session state, current turn, and knowledge map."""
        try:
            res = supabase_client.table("sessions").select("*").eq("session_id", session_id).execute()
            if not res or not hasattr(res, "data") or not res.data:
                return {}
            row = res.data[0]
            
            # Parse knowledge map
            k_map = row.get("knowledge_map") or "{}"
            if isinstance(k_map, str):
                try:
                    k_map = json.loads(k_map)
                except Exception:
                    k_map = {}

            return {
                "session_id": session_id,
                "user_id": row.get("user_id"),
                "interview_state": row.get("interview_state") or STATE_INITIALIZING,
                "personality": row.get("personality") or "professional",
                "question_index": row.get("question_index", 1),
                "turn_count": row.get("turn_count", 0),
                "active": bool(row.get("active", True)),
                "stage": row.get("stage", "Phase 1: Greeting & Icebreaker"),
                "category": row.get("category", "General Technical"),
                "role": row.get("role", "Software Engineer"),
                "difficulty": row.get("difficulty", "Medium"),
                "questions": row.get("questions") if isinstance(row.get("questions"), list) else json.loads(row.get("questions") or "[]"),
                "responses": row.get("responses") if isinstance(row.get("responses"), list) else json.loads(row.get("responses") or "[]"),
                "feedbacks": row.get("feedbacks") if isinstance(row.get("feedbacks"), list) else json.loads(row.get("feedbacks") or "[]"),
                "knowledge_map": k_map,
                "idempotency_key": row.get("idempotency_key")
            }
        except Exception as e:
            logger.error(f"Error fetching session state for {session_id}: {e}")
            return {}

    @staticmethod
    def transition_state(supabase_client, session_id: str, new_state: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Transitions session to new_state with optional metadata update."""
        if new_state not in VALID_STATES:
            logger.warning(f"Invalid state requested: {new_state}")
            return False

        update_payload: Dict[str, Any] = {
            "interview_state": new_state,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if metadata:
            for k, v in metadata.items():
                if k in ("knowledge_map", "questions", "responses", "feedbacks", "scores") and isinstance(v, (dict, list)):
                    update_payload[k] = json.dumps(v)
                else:
                    update_payload[k] = v

        try:
            supabase_client.table("sessions").update(update_payload).eq("session_id", session_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to transition session {session_id} to {new_state}: {e}")
            return False

    @staticmethod
    def check_idempotency(supabase_client, session_id: str, request_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Checks if request_id has already been executed for this session.
        If matched, returns previously recorded turn result.
        """
        if not request_id:
            return None

        try:
            res = supabase_client.table("interview_turns").select("*").eq("session_id", session_id).eq("id", request_id).execute()
            if res and hasattr(res, "data") and res.data:
                row = res.data[0]
                eval_data = row.get("evaluation_json")
                if isinstance(eval_data, str):
                    try:
                        eval_data = json.loads(eval_data)
                    except Exception:
                        pass
                return {
                    "is_cached": True,
                    "turn_number": row.get("turn_number"),
                    "question": row.get("question_text"),
                    "feedback": eval_data,
                    "score": row.get("score"),
                    "decision": row.get("decision")
                }
        except Exception as e:
            logger.warning(f"Idempotency check notice for {session_id}: {e}")
        return None

    @staticmethod
    def record_turn(
        supabase_client,
        session_id: str,
        turn_number: int,
        question_text: str,
        candidate_response: str,
        intent: str,
        decision: str,
        score: float,
        accuracy_score: int,
        evaluation: Dict[str, Any],
        stage: str,
        request_id: Optional[str] = None
    ) -> bool:
        """Records an immutable relational turn audit record."""
        turn_id = request_id or f"turn_{session_id}_{turn_number}_{int(datetime.now(timezone.utc).timestamp())}"
        turn_record = {
            "id": turn_id,
            "session_id": session_id,
            "turn_number": turn_number,
            "question_text": question_text,
            "question_type": evaluation.get("question_type", "Technical"),
            "stage": stage,
            "candidate_response": candidate_response,
            "intent": intent,
            "decision": decision,
            "score": float(score),
            "accuracy_score": int(accuracy_score),
            "evaluation_json": json.dumps(evaluation) if isinstance(evaluation, dict) else str(evaluation),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            supabase_client.table("interview_turns").insert(turn_record).execute()
            # Increment turn_count and save idempotency key
            supabase_client.table("sessions").update({
                "turn_count": turn_number,
                "idempotency_key": turn_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("session_id", session_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to record turn {turn_number} for {session_id}: {e}")
            return False

    @staticmethod
    def recover_session(supabase_client, session_id: str) -> Dict[str, Any]:
        """
        Restores full session state after network disconnect or tab reload.
        Returns latest active question, stage, turn history, and interview state.
        """
        state = InterviewStateService.get_session_state(supabase_client, session_id)
        if not state:
            return {"error": "Session not found", "recovered": False}

        questions = state.get("questions") or []
        responses = state.get("responses") or []
        feedbacks = state.get("feedbacks") or []
        current_q = questions[-1] if questions else None

        return {
            "recovered": True,
            "session_id": session_id,
            "interview_state": state.get("interview_state"),
            "personality": state.get("personality"),
            "current_question": current_q,
            "question_number": state.get("question_index", len(questions)),
            "turn_count": state.get("turn_count", len(responses)),
            "stage": state.get("stage"),
            "role": state.get("role"),
            "category": state.get("category"),
            "difficulty": state.get("difficulty"),
            "answered_count": len(responses),
            "history_summary": [
                {
                    "turn": i + 1,
                    "question": questions[i] if i < len(questions) else "",
                    "answer_preview": (responses[i][:60] + "...") if i < len(responses) and len(responses[i]) > 60 else (responses[i] if i < len(responses) else ""),
                    "score": feedbacks[i].get("score") if i < len(feedbacks) and isinstance(feedbacks[i], dict) else None
                }
                for i in range(max(len(questions), len(responses)))
            ]
        }

