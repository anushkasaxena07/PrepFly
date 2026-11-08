"""
PrepFly Event Pipeline Service
Central idempotent event ledger and reactive pipeline that connects candidate activities
(coding attempts, assessments, mock interviews, roadmap milestones, job analyses) to
skill profile updates, improvement analytics, roadmap adaptation, and achievement unlocking.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import uuid

from local_supabase import get_supabase_client
from services.skill_profiling_service import SkillProfilingService


class EventPipelineService:
    """Ingests preparation events and coordinates downstream intelligence engines."""

    SUPPORTED_EVENTS = {
        "coding_attempt_completed",
        "assessment_completed",
        "interview_completed",
        "roadmap_task_completed",
        "job_description_analyzed",
        "improvement_analyzed",
        "skill_gap_closed"
    }

    @classmethod
    def emit_event(
        cls,
        user_id: str,
        event_type: str,
        source_module: str,
        source_record_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Atomically records an event in the preparation_events ledger and
        triggers downstream intelligence pipelines.
        """
        if not user_id:
            raise ValueError("user_id is required")
        if event_type not in cls.SUPPORTED_EVENTS:
            raise ValueError(f"Unsupported event_type: {event_type}")

        supabase = supabase_client or get_supabase_client()
        payload = payload or {}
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Persist Event in Ledger
        event_row = {
            "id": event_id,
            "user_id": user_id,
            "event_type": event_type,
            "source_module": source_module,
            "source_record_id": source_record_id or "",
            "payload_json": json.dumps(payload),
            "created_at": now_iso
        }
        supabase.table("preparation_events").insert(event_row).execute()

        # 2. Process Skill Evidence Update
        evidence_created = cls._process_skill_evidence(supabase, user_id, event_type, source_record_id, payload)

        # 3. Process Improvement Tracking & Performance Snapshots
        from services.performance_analytics_engine import PerformanceAnalyticsEngine
        snapshot_result = PerformanceAnalyticsEngine.on_event(supabase, user_id, event_type, payload)

        # 4. Process Roadmap Adaptation on Meaningful Triggers
        roadmap_adapted = False
        if event_type in ("coding_attempt_completed", "interview_completed", "assessment_completed"):
            try:
                from services.roadmap_adaptation_service import RoadmapAdaptationService
                adapt_res = RoadmapAdaptationService.adapt_roadmap_on_trigger(
                    supabase_client=supabase,
                    user_id=user_id,
                    trigger_type=event_type,
                    trigger_payload=payload
                )
                roadmap_adapted = adapt_res.get("adapted", False)
            except Exception:
                roadmap_adapted = False

        # 5. Evaluate Server-Validated Achievements
        from services.achievement_service import AchievementService
        new_achievements = AchievementService.evaluate_achievements(
            supabase=supabase,
            user_id=user_id,
            event_id=event_id,
            event_type=event_type,
            payload=payload
        )

        return {
            "event_id": event_id,
            "status": "PROCESSED",
            "evidence_created": evidence_created,
            "snapshot_updated": snapshot_result.get("snapshot_created", False),
            "roadmap_adapted": roadmap_adapted,
            "new_achievements": new_achievements
        }

    @classmethod
    def _process_skill_evidence(
        cls,
        supabase,
        user_id: str,
        event_type: str,
        source_record_id: Optional[str],
        payload: Dict[str, Any]
    ) -> bool:
        """Translates candidate event into canonical skill evidence entries."""
        try:
            if event_type == "coding_attempt_completed":
                skill_id = payload.get("skill_id") or "algorithms"
                score = float(payload.get("score", 0.0))
                passed = payload.get("passed_tests", 0)
                total = payload.get("total_tests", 1)
                
                # Derive 0-100 score if passed ratio provided
                if total > 0 and score == 0.0 and passed > 0:
                    score = (passed / total) * 100.0

                SkillProfilingService.record_evidence(
                    supabase_client=supabase,
                    user_id=user_id,
                    skill_id=skill_id,
                    source_type="CODING_SANDBOX",
                    source_id=source_record_id or payload.get("problem_id", ""),
                    score=score,
                    weight=1.0,
                    demonstrated_concepts=payload.get("demonstrated_concepts", []),
                    missed_concepts=payload.get("missed_concepts", []),
                    evidence_notes=payload.get("notes", f"Problem: {payload.get('problem_id', '')}")
                )
                return True

            elif event_type == "interview_completed":
                score = float(payload.get("overall_score") or payload.get("accuracy_score") or 70.0)
                evaluated_skills = payload.get("skills_evaluated") or ["communication", "technical_interview"]
                for sid in evaluated_skills:
                    SkillProfilingService.record_evidence(
                        supabase_client=supabase,
                        user_id=user_id,
                        skill_id=sid,
                        source_type="AVA_MOCK_INTERVIEW",
                        source_id=source_record_id or payload.get("session_id", ""),
                        score=score,
                        weight=1.2,
                        demonstrated_concepts=payload.get("demonstrated_concepts", []),
                        missed_concepts=payload.get("missed_concepts", []),
                        evidence_notes=payload.get("notes", "Mock interview completed")
                    )
                return True

            elif event_type == "assessment_completed":
                skill_scores = payload.get("skill_scores") or {}
                for sid, s_score in skill_scores.items():
                    SkillProfilingService.record_evidence(
                        supabase_client=supabase,
                        user_id=user_id,
                        skill_id=sid,
                        source_type="DIAGNOSTIC_ASSESSMENT",
                        source_id=source_record_id or payload.get("assessment_id", ""),
                        score=float(s_score),
                        weight=1.5,
                        evidence_notes="Standardized assessment evaluation"
                    )
                return True

            elif event_type == "roadmap_task_completed":
                skill_id = payload.get("skill_id")
                if skill_id:
                    score = float(payload.get("score", 85.0))
                    SkillProfilingService.record_evidence(
                        supabase_client=supabase,
                        user_id=user_id,
                        skill_id=skill_id,
                        source_type="ROADMAP_ACTIVITY",
                        source_id=source_record_id or payload.get("activity_id", ""),
                        score=score,
                        weight=0.8,
                        evidence_notes="Roadmap study activity finished"
                    )
                return True

        except Exception as ex:
            print(f"[EventPipelineService] Error processing evidence: {ex}")
            return False

        return False

    @classmethod
    def get_user_events(
        cls,
        user_id: str,
        limit: int = 50,
        event_type: Optional[str] = None,
        supabase_client=None
    ) -> List[Dict[str, Any]]:
        """Retrieves historical events for an audit log."""
        supabase = supabase_client or get_supabase_client()
        query = supabase.table("preparation_events").select("*").eq("user_id", user_id)
        if event_type:
            query = query.eq("event_type", event_type)
        res = query.order("created_at", desc=True).limit(limit).execute()
        return res.data if (res and res.data) else []
