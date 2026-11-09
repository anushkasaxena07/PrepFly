"""
Mentor Conversation Service for PrepFly Adaptive AI Mentor.
Manages persistent, intelligent contextual mentoring sessions, intent recognition,
context summarization, and personalized preparation coaching.
"""

from typing import Dict, List, Optional, Any
import json
import uuid
from datetime import datetime, timezone

from services.ai_service import safe_invoke_llm
from services.skill_profiling_service import SkillProfilingService
from services.candidate_profile_service import CandidateProfileService
from services.roadmap_engine import SchedulingEngine
from local_supabase import get_supabase_client


# Contextual Quick Action Prompt Intents
INTENT_EXPLAIN_FROM_SCRATCH = "explain_from_scratch"
INTENT_REAL_WORLD_EXAMPLE = "real_world_example"
INTENT_HARDER_QUESTION = "harder_question"
INTENT_EVALUATE_ANSWER = "evaluate_answer"
INTENT_TIME_BUDGET_30MIN = "time_budget_30min"
INTENT_PREPARE_TOMORROW = "prepare_tomorrow"
INTENT_MOCK_INTERVIEW = "mock_interview"
INTENT_GENERAL_CHAT = "general_chat"


class MentorService:
    """Manages persistent mentor conversations with context-rich prompting and summarization."""

    @classmethod
    def start_or_resume_conversation(
        cls,
        user_id: str,
        title: Optional[str] = None,
        context_metadata: Optional[Dict[str, Any]] = None,
        supabase_client: Any = None
    ) -> Dict[str, Any]:
        """Creates a new conversation or resumes the most recent active thread for the user."""
        client = supabase_client or get_supabase_client()

        # Check for existing active conversation
        try:
            res = client.table("mentor_conversations").select("*").eq("user_id", user_id).order("updated_at", desc=True).limit(1).execute()
            if res and res.data and len(res.data) > 0:
                conv = res.data[0]
                # If title provided and conversation is default, update title
                if title and conv.get("title") == "Interview Preparation Mentorship":
                    client.table("mentor_conversations").update({"title": title}).eq("id", conv["id"]).execute()
                    conv["title"] = title
                return conv
        except Exception:
            pass

        # Create new conversation
        conv_id = str(uuid.uuid4())
        conv_title = title or "Interview Preparation Mentorship"
        record = {
            "id": conv_id,
            "user_id": user_id,
            "title": conv_title,
            "context_summary": "Initiated interview mentorship session.",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            client.table("mentor_conversations").insert(record).execute()
        except Exception:
            pass

        # Add initial welcome greeting message
        welcome_text = (
            f"Hello! I am your PrepFly AI Interview Mentor. "
            f"I track your target company, role requirements, and current skill mastery. "
            f"Whether you need concepts explained from scratch, practical code walkthroughs, "
            f"rubric-based feedback, or daily time management, I'm here to guide you."
        )
        cls.save_message(
            conversation_id=conv_id,
            user_id=user_id,
            role="assistant",
            content=welcome_text,
            intent="welcome",
            supabase_client=client
        )

        return record

    @classmethod
    def get_conversation_messages(
        cls,
        conversation_id: str,
        limit: int = 50,
        supabase_client: Any = None
    ) -> List[Dict[str, Any]]:
        """Retrieves recent chronological messages for a conversation thread."""
        client = supabase_client or get_supabase_client()
        try:
            res = client.table("mentor_messages").select("*").eq("conversation_id", conversation_id).order("created_at", desc=False).limit(limit).execute()
            if res and res.data:
                return res.data
        except Exception:
            pass
        return []

    @classmethod
    def save_message(
        cls,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        context_payload: Optional[Dict[str, Any]] = None,
        tokens_used: int = 0,
        supabase_client: Any = None
    ) -> Dict[str, Any]:
        """Saves a message in the mentor conversation history."""
        client = supabase_client or get_supabase_client()
        msg_id = str(uuid.uuid4())
        msg = {
            "id": msg_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "intent": intent or INTENT_GENERAL_CHAT,
            "context_payload": json.dumps(context_payload or {}),
            "tokens_used": tokens_used,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            client.table("mentor_messages").insert(msg).execute()
            client.table("mentor_conversations").update({
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", conversation_id).execute()
        except Exception:
            pass
        return msg

    @classmethod
    def build_candidate_context(
        cls,
        user_id: str,
        supabase_client: Any = None
    ) -> Dict[str, Any]:
        """Aggregates candidate profile, proficiency, top skill gaps, and active roadmap state."""
        client = supabase_client or get_supabase_client()

        profile = CandidateProfileService.get_profile(user_id, client) or {}
        proficiencies = SkillProfilingService.get_candidate_proficiencies(user_id, client)
        gaps = SkillProfilingService.get_skill_gaps(user_id, profile.get("target_role", "Software Development Engineer"), client)
        recurring_mistakes = SkillProfilingService.get_recurring_mistakes(user_id, client)
        active_activities = []
        try:
            act_res = client.table("roadmap_activities").select("*").eq("user_id", user_id).neq("status", "COMPLETED").limit(10).execute()
            if act_res and act_res.data:
                active_activities = act_res.data
        except Exception:
            pass

        return {
            "target_role": profile.get("target_role", "Software Development Engineer"),
            "target_company": profile.get("target_company", "Top Tech Firm"),
            "experience_level": profile.get("experience_level", "Mid-Level"),
            "target_date": profile.get("target_date", "30 days"),
            "daily_minutes": profile.get("daily_minutes", 60),
            "top_skill_gaps": [g.get("skill_name") or g.get("skill_id") for g in gaps[:5]],
            "weak_skills": [s for s, p in proficiencies.items() if p < 50.0],
            "mastered_skills": [s for s, p in proficiencies.items() if p >= 80.0],
            "recurring_mistakes": recurring_mistakes[:3],
            "active_activities_count": len(active_activities)
        }

    @classmethod
    def detect_intent(cls, message_text: str) -> str:
        """Classifies user message intent into structured mentor command patterns."""
        t = (message_text or "").lower().strip()
        if any(k in t for k in ["from scratch", "explain from scratch", "simple explanation", "eli5", "what is"]):
            return INTENT_EXPLAIN_FROM_SCRATCH
        elif any(k in t for k in ["real world", "real-world", "production example", "how is this used"]):
            return INTENT_REAL_WORLD_EXAMPLE
        elif any(k in t for k in ["harder", "more difficult", "advanced question", "challenge me", "harder question"]):
            return INTENT_HARDER_QUESTION
        elif any(k in t for k in ["evaluate", "check my answer", "review my code", "is this correct", "grade my"]):
            return INTENT_EVALUATE_ANSWER
        elif any(k in t for k in ["30 mins", "30 minutes", "short on time", "quick session", "have 30 mins"]):
            return INTENT_TIME_BUDGET_30MIN
        elif any(k in t for k in ["tomorrow", "prepare for tomorrow", "next day", "what should i do tomorrow"]):
            return INTENT_PREPARE_TOMORROW
        elif any(k in t for k in ["mock interview", "conduct a mock", "interview me", "simulate interview"]):
            return INTENT_MOCK_INTERVIEW
        return INTENT_GENERAL_CHAT

    @classmethod
    def send_mentor_message(
        cls,
        user_id: str,
        conversation_id: str,
        user_message: str,
        active_activity: Optional[Dict[str, Any]] = None,
        supabase_client: Any = None
    ) -> Dict[str, Any]:
        """
        Receives candidate input, retrieves compact context, identifies intent,
        synthesizes high-yield mentor guidance via Gemini, and returns structured advice.
        """
        client = supabase_client or get_supabase_client()
        intent = cls.detect_intent(user_message)

        # 1. Save candidate message
        cls.save_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=user_message,
            intent=intent,
            supabase_client=client
        )

        # 2. Build candidate context
        context = cls.build_candidate_context(user_id, client)
        if active_activity:
            context["active_topic"] = active_activity.get("title")
            context["active_skill_id"] = active_activity.get("skill_id")
            context["active_difficulty"] = active_activity.get("difficulty")

        # 3. Retrieve conversation history (recent 6 turns)
        history = cls.get_conversation_messages(conversation_id, limit=6, supabase_client=client)
        dialogue_history = []
        for m in history[:-1]:  # exclude the just saved user message
            role_label = "Student" if m.get("role") == "user" else "AI Mentor"
            dialogue_history.append(f"{role_label}: {m.get('content', '')}")
        dialogue_block = "\n".join(dialogue_history) if dialogue_history else "No prior history."

        # 4. Construct high-yield mentor prompt
        system_prompt = (
            "You are PrepFly AI Mentor, an elite, highly supportive, and rigorous technical interview coach. "
            "You possess deep expertise in algorithms, system design, machine learning, CS fundamentals, and behavioral frameworks.\n\n"
            f"Candidate Context:\n"
            f"- Target Role: {context.get('target_role')}\n"
            f"- Target Company: {context.get('target_company')}\n"
            f"- Experience Level: {context.get('experience_level')}\n"
            f"- Daily Budget: {context.get('daily_minutes')} mins\n"
            f"- Top Skill Gaps: {', '.join(context.get('top_skill_gaps') or ['None identified yet'])}\n"
            f"- Active Topic: {context.get('active_topic', 'General Interview Preparation')}\n"
            f"- Detected Intent: {intent}\n\n"
            "Guiding Principles:\n"
            "1. Be direct, clear, and encouraging. Never give vague advice like 'study more'.\n"
            "2. When explaining, start with the core intuition, followed by the exact technical invariant or mechanism.\n"
            "3. If code is requested, provide clean, idiomatic code with time and space complexity analysis.\n"
            "4. Keep answers focused and actionable to respect the candidate's daily preparation budget.\n"
            "5. If intent is 'time_budget_30min', give a tightly prioritized 30-minute breakdown (10m Concept, 15m Practice, 5m Review)."
        )

        user_prompt = (
            f"Recent Dialogue:\n{dialogue_block}\n\n"
            f"Student Message: {user_message}\n\n"
            "Provide your tailored coaching response:"
        )

        try:
            mentor_reply = safe_invoke_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.4
            )
        except Exception:
            mentor_reply = (
                f"Great question regarding {context.get('target_role')} preparation at {context.get('target_company')}! "
                f"Focus on the underlying invariant: state your data structures clearly, analyze your O(N) time and space complexity bounds, "
                f"and ensure you handle boundary edge cases. Let me know if you would like a code walkthrough or a targeted practice challenge."
            )

        # 5. Suggested follow-up quick pills based on intent
        suggested_pills = [
            "Explain from scratch",
            "Show real-world example",
            "Give me a harder question",
            "I have 30 mins today"
        ]
        if intent == INTENT_EXPLAIN_FROM_SCRATCH:
            suggested_pills = ["Show code example", "Common interview pitfalls", "Give me a practice problem"]
        elif intent == INTENT_REAL_WORLD_EXAMPLE:
            suggested_pills = ["How would an interviewer ask this?", "What are the trade-offs?", "Next roadmap topic"]
        elif intent == INTENT_TIME_BUDGET_30MIN:
            suggested_pills = ["Start 10m concept review", "Quick 15m code challenge", "Prepare for tomorrow"]

        # 6. Save and return assistant response
        assistant_record = cls.save_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=mentor_reply,
            intent=intent,
            context_payload={"suggested_pills": suggested_pills},
            tokens_used=len(mentor_reply.split()),
            supabase_client=client
        )

        return {
            "message": assistant_record,
            "suggested_pills": suggested_pills,
            "intent": intent,
            "conversation_id": conversation_id
        }
