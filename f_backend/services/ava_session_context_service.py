"""
Ava Session Context Service: Assembles, caches, and persists structured
session context objects combining Track, Personality, and Grounded Resume Facts.
Enforces hard prompt directives so Gemini never wanders outside track or ignores personality.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone

from interviewer_config.track_configs import resolve_track, validate_question_against_track
from interviewer_config.personality_configs import resolve_personality
from services.resume_grounding_service import ResumeGroundingService


class AvaSessionContextService:
    """Manages immutable, structured session context for Ava AI interviews."""

    CONTEXT_VERSION = "v1.0"

    @classmethod
    def build_session_context(
        cls,
        session_id: str,
        track_identifier: Optional[str] = None,
        personality_identifier: Optional[str] = None,
        candidate_name: str = "Candidate",
        resume_text: str = "",
        job_description: str = "",
        target_role: Optional[str] = None,
        target_level: str = "Mid-Level (2-4 Years)",
        time_budget_minutes: Optional[int] = None,
        consent_flags: Optional[Dict[str, Any]] = None,
        language: str = "en-US"
    ) -> Dict[str, Any]:
        """
        Builds the unified session context object for Ava.
        Persisted in session blueprint_json; governs all downstream turn prompts.
        """
        track_cfg = resolve_track(track_identifier)
        personality_cfg = resolve_personality(personality_identifier)
        fact_sheet = ResumeGroundingService.extract_fact_sheet(resume_text, candidate_name)

        final_time_budget = time_budget_minutes or track_cfg.get("time_budget_minutes", 30)
        final_role = target_role or track_cfg.get("display_name", "Software Engineer")

        consent = consent_flags or {
            "affirmative_consent": True,
            "dpdp_compliant": True,
            "audio_retention_acknowledged": True
        }

        # Candidate display name sanitization (Prompt 2 R6 priority)
        clean_name = candidate_name.strip() if candidate_name and candidate_name.lower() != "candidate" else "Candidate"
        first_name = clean_name.split()[0] if clean_name != "Candidate" else ""

        return {
            "version": cls.CONTEXT_VERSION,
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "candidate": {
                "display_name": clean_name,
                "first_name": first_name or clean_name,
                "target_role": final_role,
                "target_level": target_level
            },
            "track": track_cfg,
            "personality": personality_cfg,
            "resume_facts": fact_sheet,
            "job_description_snippet": job_description[:1500] if job_description else "",
            "constraints": {
                "time_budget_minutes": final_time_budget,
                "language": language,
                "consent_flags": consent,
                "max_questions": track_cfg.get("default_question_count", 5)
            }
        }

    @classmethod
    def generate_prompt_directives(cls, session_context: Dict[str, Any], current_turn: int = 1) -> str:
        """
        Compiles track, personality, and resume facts into an unambiguous system directive
        for the LLM turn prompt. Guarantees track adherence and tone calibration.
        """
        track = session_context["track"]
        personality = session_context["personality"]
        candidate = session_context["candidate"]
        facts = session_context["resume_facts"].get("facts", [])

        allowed_topics_str = ", ".join(track.get("allowed_topics", []))
        forbidden_topics_str = ", ".join(track.get("forbidden_topics", []))

        # Format top 5 verified resume facts
        top_facts = facts[:5]
        fact_lines = [f"- [{f['fact_id']}] ({f['category']}): {f['claim_text']}" for f in top_facts]
        fact_block = "\n".join(fact_lines) if fact_lines else "None (No resume facts available)"

        directives = f"""=== AVA INTERVIEW CONTRACT & BOUNDARIES (STRICT CODE ENFORCED) ===
INTERVIEWER IDENTITY: Ava (PrepFly AI Interviewer)
CANDIDATE NAME: {candidate['display_name']} (Use '{candidate['first_name']}' naturally)
ROLE: {candidate['target_role']} | LEVEL: {candidate['target_level']}

1. TRACK BOUNDARY: {track['display_name']} (Track ID: {track['track_id']})
- MANDATORY TOPICS: {allowed_topics_str}
- FORBIDDEN TOPICS: {forbidden_topics_str}
- TRACK OPENING SCOPE: "{track['opening_scope_sentence']}"
- VIOLATION RULE: You MUST NOT ask questions outside {track['display_name']}. Any off-track question will be rejected by code guards.

2. PERSONALITY CALIBRATION: {personality['name']} ({personality['badge']})
- WARMTH: {personality['warmth']:.2f} / 1.00 | FORMALITY: {personality['formality']:.2f} / 1.00 | DIRECTNESS: {personality['directness']:.2f} / 1.00
- PRAISE POLICY: {personality['praise_policy']}
- FOLLOW-UP DEPTH: {personality['followup_depth']} follow-ups maximum
- PUSHBACK STYLE: {personality['pushback_style']} (Challenge rate: {personality['challenge_rate']:.2f})
- HINT POLICY: {personality['hint_policy']}
- VOCABULARY LEVEL: {personality['vocabulary_level']} | SENIORITY BAR: {personality['seniority_bar']}
- PACING / TONE: Adhere strictly to the {personality['name']} voice profile. Never sound robotic or generic.

3. VERIFIED RESUME FACTS (GROUNDING ANCHORS):
{fact_block}
- GROUNDING RULE: For resume-based questions, cite the candidate's exact project or tech stack. Never invent facts, companies, or tools not listed above.
===================================================================="""
        return directives

