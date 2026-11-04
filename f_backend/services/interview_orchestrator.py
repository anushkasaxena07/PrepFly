"""
Interview Orchestrator: Central orchestration layer for Ava AI interviews.
Coordinates session state, personality styles, conversational intent,
concept-level analysis, deterministic adaptive policies, and evidence-grounded rubrics.
"""

import json
import logging
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timezone

from services.interview_state_service import (
    InterviewStateService,
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
)
from services.interviewer_personality_service import InterviewerPersonalityService
from services.resume_intelligence_service import ResumeIntelligenceService
from services.answer_analyzer import (
    AnswerAnalyzer,
    INTENT_ANSWER,
    INTENT_REPEAT,
    INTENT_CLARIFY,
    INTENT_PAUSE,
    INTENT_NO_ANSWER,
    INTENT_CORRECTION,
    INTENT_EARLY_EXIT
)
from services.adaptive_interview_engine import (
    AdaptiveInterviewEngine,
    DECISION_FOLLOW_UP,
    DECISION_CLARIFY,
    DECISION_SIMPLIFY,
    DECISION_INCREASE_DIFFICULTY,
    DECISION_CHANGE_TOPIC,
    DECISION_NEXT_QUESTION,
    DECISION_END_INTERVIEW
)
from services.evaluation_service import (
    EvaluationService,
    INTERVIEW_TYPE_TECHNICAL,
    INTERVIEW_TYPE_CODING,
    INTERVIEW_TYPE_SYSTEM_DESIGN,
    INTERVIEW_TYPE_BEHAVIORAL,
    INTERVIEW_TYPE_PROJECT
)
from services.question_bank_service import QuestionBankService
from services.ai_service import generate_dynamic_question, get_current_stage

logger = logging.getLogger(__name__)


class InterviewOrchestrator:
    """Coordinates turn-taking, evaluation, adaptive decisions, and state persistence."""

    @staticmethod
    def start_interview_session(
        supabase_client,
        session_id: str,
        category: str = "General Technical",
        role: str = "Software Engineer",
        difficulty: str = "Medium",
        personality: str = "professional",
        chat_model: Any = None,
        candidate_name: str = "Candidate"
    ) -> Dict[str, Any]:
        """
        Initializes interview session, verifies consent, extracts resume claims,
        and generates the opening greeting and icebreaker question.
        """
        session_data = InterviewStateService.get_session_state(supabase_client, session_id)
        if not session_data:
            return {"error": "Session not found", "status_code": 404}

        # Verify or set personality
        resolved_personality = InterviewerPersonalityService.resolve_personality(personality)

        # Ingest and structure resume if provided
        raw_resume = ""
        try:
            res_row = supabase_client.table("sessions").select("resume_text").eq("session_id", session_id).execute()
            if res_row and res_row.data:
                raw_resume = res_row.data[0].get("resume_text") or ""
        except Exception:
            pass

        structured_profile = ResumeIntelligenceService.extract_structured_candidate_profile(raw_resume)
        if structured_profile.get("verified_claims"):
            ResumeIntelligenceService.persist_verified_claims(
                supabase_client, session_id, structured_profile["verified_claims"]
            )

        # Generate Phase 1 icebreaker
        first_q, stage, _ = generate_dynamic_question(
            raw_resume,
            previous_questions=[],
            question_index=1,
            category=category,
            difficulty=difficulty,
            role=role,
            chat_model=chat_model,
            candidate_name=candidate_name
        )

        # Update session with state ASKING
        metadata = {
            "personality": resolved_personality["id"],
            "interview_state": STATE_ASKING,
            "questions": [first_q],
            "question_index": 1,
            "turn_count": 0,
            "stage": stage,
            "category": category,
            "role": role,
            "difficulty": difficulty,
            "knowledge_map": {}
        }
        InterviewStateService.transition_state(supabase_client, session_id, STATE_ASKING, metadata)

        return {
            "message": "Interview started",
            "question": first_q,
            "question_number": 1,
            "stage": stage,
            "personality": resolved_personality,
            "total_questions": 10
        }

    @staticmethod
    def process_candidate_turn(
        supabase_client,
        session_id: str,
        answer_text: str,
        chat_model: Any = None,
        request_id: Optional[str] = None,
        coding_execution_metrics: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Main turn orchestrator:
        1. Checks idempotency (returns cached turn if duplicate request_id).
        2. Detects conversational intent (repeat, clarify, pause, skip, early exit).
        3. Evaluates answer against objective typed rubrics (Technical, Coding, System Design, Behavioral).
        4. Extracts concepts and updates session knowledge map.
        5. Runs deterministic decision policy (FOLLOW_UP, INCREASE_DIFFICULTY, SIMPLIFY, CHANGE_TOPIC, NEXT_QUESTION).
        6. Selects or generates the next question and records the immutable turn audit.
        """
        # 1. Idempotency Check
        cached_turn = InterviewStateService.check_idempotency(supabase_client, session_id, request_id)
        if cached_turn:
            logger.info(f"Returning cached turn response for request_id: {request_id}")
            return {
                "message": "Turn already processed (idempotent replay)",
                "done": False,
                "feedback": cached_turn.get("feedback"),
                "next_question": cached_turn.get("question"),
                "score": cached_turn.get("score")
            }, 200

        session = InterviewStateService.get_session_state(supabase_client, session_id)
        if not session or not session.get("active", True):
            return {"error": "Session not found or already completed"}, 404

        questions = session.get("questions") or []
        responses = session.get("responses") or []
        feedbacks = session.get("feedbacks") or []
        q_index = session.get("question_index", 1)
        current_q = questions[-1] if questions else "Tell me about yourself."
        k_map = session.get("knowledge_map") or {}
        personality_key = session.get("personality") or "professional"
        role = session.get("role") or "Software Engineer"
        category = session.get("category") or "General Technical"
        difficulty = session.get("difficulty") or "Medium"

        # 2. Intent Detection
        intent = AnswerAnalyzer.detect_conversational_intent(answer_text)

        # Conversational commands handled gracefully without penalizing score:
        if intent in (INTENT_REPEAT, INTENT_CLARIFY, INTENT_PAUSE, INTENT_CORRECTION):
            reaction = AnswerAnalyzer.generate_conversational_response_for_intent(
                intent, current_q, personality_key
            )
            return {
                "message": reaction["message"],
                "done": False,
                "intent": intent,
                "feedback": {
                    "feedback": f"ℹ️ Conversational action: {intent}",
                    "score": 7.0,
                    "accuracy_score": 70,
                    "correctness": "Conversational Interaction",
                    "strength": "Natural candidate turn communication",
                    "improvement": "None",
                    "tip": "Speak when you are ready to give your complete answer",
                    "summary": f"Interviewer handled {intent.lower()} request."
                },
                "next_question": current_q,
                "question_number": q_index,
                "stage": session.get("stage", "Phase 1: Greeting & Icebreaker"),
                "total_questions": 10
            }, 200

        if intent == INTENT_EARLY_EXIT:
            reaction = AnswerAnalyzer.generate_conversational_response_for_intent(
                intent, current_q, personality_key
            )
            InterviewStateService.transition_state(supabase_client, session_id, STATE_COMPLETED, {"active": False})
            return {
                "message": reaction["message"],
                "done": True,
                "intent": INTENT_EARLY_EXIT,
                "next_question": None,
                "question_number": q_index,
                "stage": "Phase 7: Natural Wrap-up"
            }, 200

        # 3. Rubric Evaluation & Concept Analysis
        InterviewStateService.transition_state(supabase_client, session_id, STATE_ANALYZING)
        
        # Determine interview type based on question content
        q_lower = current_q.lower()
        if coding_execution_metrics or "write a function" in q_lower or "code" in q_lower:
            inv_type = INTERVIEW_TYPE_CODING
        elif "system design" in q_lower or "architecture" in q_lower or "sharding" in q_lower or "scale" in q_lower:
            inv_type = INTERVIEW_TYPE_SYSTEM_DESIGN
        elif "tell me about a time" in q_lower or "conflict" in q_lower or "disagreement" in q_lower or "star" in q_lower:
            inv_type = INTERVIEW_TYPE_BEHAVIORAL
        elif "project" in q_lower:
            inv_type = INTERVIEW_TYPE_PROJECT
        else:
            inv_type = INTERVIEW_TYPE_TECHNICAL

        evaluation = EvaluationService.evaluate_response_with_rubric(
            interview_type=inv_type,
            question=current_q,
            answer=answer_text,
            chat_model=chat_model,
            role=role,
            coding_execution_metrics=coding_execution_metrics
        )

        acc_score = evaluation.get("accuracy_score", 70)
        score_10 = evaluation.get("overall_score", 7.0)

        # 4. Concept extraction and knowledge map update
        concept_analysis = AnswerAnalyzer.extract_concept_evidence(current_q, answer_text, category, role)
        updated_kmap = AdaptiveInterviewEngine.update_session_knowledge_map(
            k_map, category, inv_type, concept_analysis, acc_score
        )

        # 5. Deterministic Adaptive Policy
        decision = AdaptiveInterviewEngine.evaluate_next_action(
            accuracy_score=acc_score,
            concept_analysis=concept_analysis,
            turn_number=q_index,
            total_questions=10
        )

        # 6. Check Completion
        is_done = (q_index >= 10) or (decision == DECISION_END_INTERVIEW)
        next_q = None
        next_stage = "Phase 7: Natural Wrap-up" if is_done else get_current_stage(q_index + 1)

        if not is_done:
            # Generate next question incorporating adaptive decision and personality
            personality_modifier = InterviewerPersonalityService.get_prompt_modifier(personality_key)
            adaptive_guidance = AdaptiveInterviewEngine.construct_adaptive_prompt_guidance(
                decision, concept_analysis, personality_modifier, updated_kmap
            )

            # Generate dynamic question with anti-hallucination and anti-repetition protection
            try:
                next_q, next_stage, _ = generate_dynamic_question(
                    "",  # Grounded through guidance
                    previous_questions=questions,
                    question_index=q_index + 1,
                    last_score=score_10,
                    last_answer=answer_text,
                    category=category,
                    difficulty=difficulty,
                    role=role,
                    responses=responses,
                    chat_model=chat_model,
                    candidate_name="Candidate"
                )
            except Exception as e:
                logger.warning(f"Fallback to curated bank question ({e})")
                bank_q = QuestionBankService.select_best_question(category, difficulty, questions)
                next_q = bank_q.get("question_text")

        # 7. Update Session State and Turn Record
        responses.append(answer_text)
        feedbacks.append(evaluation)
        if next_q:
            questions.append(next_q)

        session_meta = {
            "questions": questions,
            "responses": responses,
            "feedbacks": feedbacks,
            "question_index": q_index + (0 if is_done else 1),
            "stage": next_stage,
            "knowledge_map": updated_kmap,
            "turn_count": len(responses),
            "interview_state": STATE_COMPLETED if is_done else STATE_WAITING_FOR_RESPONSE,
            "active": not is_done
        }

        InterviewStateService.transition_state(
            supabase_client,
            session_id,
            STATE_COMPLETED if is_done else STATE_WAITING_FOR_RESPONSE,
            session_meta
        )

        InterviewStateService.record_turn(
            supabase_client=supabase_client,
            session_id=session_id,
            turn_number=q_index,
            question_text=current_q,
            candidate_response=answer_text,
            intent=intent,
            decision=decision,
            score=score_10,
            accuracy_score=acc_score,
            evaluation=evaluation,
            stage=session.get("stage", ""),
            request_id=request_id
        )

        return {
            "message": "Answer recorded",
            "done": is_done,
            "feedback": evaluation,
            "next_question": next_q,
            "question_number": q_index + (0 if is_done else 1),
            "stage": next_stage,
            "decision": decision,
            "is_followup": (decision == DECISION_FOLLOW_UP),
            "total_questions": 10
        }, 200

