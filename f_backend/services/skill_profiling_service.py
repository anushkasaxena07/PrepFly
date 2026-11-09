"""
Evidence-Based Skill Profiling Service for PrepFly Intelligence.
Calculates candidate proficiency from verifiable performance evidence.
Maintains strict separation between proficiency (0-100) and assessment confidence (0.0-1.0).
Supports flexible parameter signatures and automated Supabase client injection.
"""

from typing import Dict, List, Optional, Any, Tuple
import json
import uuid
import math
from datetime import datetime, timezone
from local_supabase import get_supabase_client
from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG

# Source Type Weights calibrated to source diagnostic fidelity
SOURCE_WEIGHTS = {
    "diagnostic_assessment": 1.0,
    "assessment": 1.0,
    "ASSESSMENT": 1.0,
    "coding_submission": 1.2,
    "coding": 1.2,
    "CODING": 1.2,
    "ava_interview": 1.0,
    "interview": 1.0,
    "MOCK_INTERVIEW": 1.0,
    "activity_completion": 0.8,
    "practice": 0.8,
    "PRACTICE": 0.8,
    "revision": 1.0,
    "REVISION": 1.0
}


class SkillProfilingService:
    """Calculates, persists, and trends candidate skill proficiency from real performance evidence."""

    @staticmethod
    def calculate_confidence(
        evidence_count: int,
        source_types: List[str],
        last_assessed_iso: Optional[str] = None
    ) -> float:
        """
        Calculates assessment confidence (0.0 to 1.0).
        Confidence scales with evidence quantity, cross-source diversity, and recency.
        A single attempt yields low confidence (~0.25); multi-attempt cross-feature yields 0.85+.
        """
        if evidence_count <= 0:
            return 0.0

        # 1. Volume Factor (diminishing returns, asymptotic to 1.0)
        vol_confidence = 1.0 - math.exp(-0.35 * evidence_count)

        # 2. Source Diversity Multiplier
        distinct_sources = len(set(s.lower() for s in source_types if s))
        diversity_factor = 1.0
        if distinct_sources >= 3:
            diversity_factor = 1.25
        elif distinct_sources == 2:
            diversity_factor = 1.15

        # 3. Recency Decay (graceful decay if unassessed for > 45 days)
        recency_multiplier = 1.0
        if last_assessed_iso:
            try:
                dt = datetime.fromisoformat(last_assessed_iso.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                days_diff = (now - dt).total_seconds() / 86400.0
                if days_diff > 60:
                    recency_multiplier = 0.90
                elif days_diff > 30:
                    recency_multiplier = 0.95
            except Exception:
                recency_multiplier = 1.0

        total_conf = min(0.98, vol_confidence * diversity_factor * recency_multiplier)
        return round(total_conf, 2)

    @classmethod
    def record_evidence(
        cls,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Records a single verifiable evidence item and recalculates the candidate's skill profile.
        Supports both (supabase_client, user_id, skill_id, ...) and (user_id=..., skill_id=..., ...)
        """
        # Signature resolution
        if len(args) >= 3 and not isinstance(args[0], str):
            supabase_client = args[0]
            user_id = args[1]
            skill_id = args[2]
            source_type = args[3] if len(args) > 3 else kwargs.get("source_type") or kwargs.get("source", "diagnostic_assessment")
            source_id = args[4] if len(args) > 4 else kwargs.get("source_id")
            score = args[5] if len(args) > 5 else kwargs.get("score", 70.0)
        else:
            supabase_client = kwargs.pop("supabase_client", None) or get_supabase_client()
            if args:
                user_id = args[0]
                skill_id = args[1] if len(args) > 1 else kwargs.pop("skill_id", "")
                score = args[2] if len(args) > 2 else kwargs.pop("score", 70.0)
                source_type = args[3] if len(args) > 3 else kwargs.pop("source_type", kwargs.pop("source", "diagnostic_assessment"))
                source_id = args[4] if len(args) > 4 else kwargs.pop("source_id", None)
            else:
                user_id = kwargs.pop("user_id", "")
                skill_id = kwargs.pop("skill_id", "")
                score = kwargs.pop("score", 70.0)
                source_type = kwargs.pop("source_type", kwargs.pop("source", "diagnostic_assessment"))
                source_id = kwargs.pop("source_id", None)

        demonstrated_concepts = kwargs.get("demonstrated_concepts") or []
        missed_concepts = kwargs.get("missed_concepts") or []
        misconceptions = kwargs.get("misconceptions") or []
        notes = kwargs.get("notes") or kwargs.get("evidence_notes", "")
        rubric_version = kwargs.get("rubric_version", "v1")
        raw_data = kwargs.get("raw_data") or {}

        if not user_id or not skill_id:
            raise ValueError("user_id and skill_id are required")

        bounded_score = max(0.0, min(100.0, float(score)))
        weight = SOURCE_WEIGHTS.get(str(source_type).lower(), SOURCE_WEIGHTS.get(str(source_type), 1.0))
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Insert into skill_evidence
        evidence_id = str(uuid.uuid4())
        evidence_record = {
            "id": evidence_id,
            "user_id": user_id,
            "skill_id": skill_id,
            "source_type": str(source_type).lower(),
            "source_id": source_id or evidence_id,
            "score": bounded_score,
            "weight": weight,
            "demonstrated_concepts": json.dumps(demonstrated_concepts),
            "missed_concepts": json.dumps(missed_concepts),
            "misconceptions": json.dumps(misconceptions),
            "evidence_notes": notes or json.dumps(raw_data),
            "rubric_version": rubric_version,
            "created_at": now_iso
        }
        supabase_client.table("skill_evidence").insert(evidence_record).execute()

        # 2. Query all evidence for this user + skill to compute weighted proficiency and confidence
        ev_res = supabase_client.table("skill_evidence").select("*").eq("user_id", user_id).eq("skill_id", skill_id).execute()
        all_evidence = ev_res.data if (ev_res and ev_res.data) else [evidence_record]

        total_weighted_score = 0.0
        total_weights = 0.0
        sources_list = []
        all_demonstrated = set()
        all_missed = set()
        history_points = []

        sorted_ev = sorted(all_evidence, key=lambda x: x.get("created_at", ""))
        for idx, ev in enumerate(sorted_ev):
            ev_score = float(ev.get("score", 0.0))
            ev_w = float(ev.get("weight", 1.0))
            recency = 1.0 + (idx / max(1, len(sorted_ev))) * 0.5
            effective_w = ev_w * recency

            total_weighted_score += ev_score * effective_w
            total_weights += effective_w
            sources_list.append(ev.get("source_type"))

            raw_d = ev.get("demonstrated_concepts")
            if isinstance(raw_d, (list, set)):
                all_demonstrated.update(raw_d)
            elif isinstance(raw_d, str) and raw_d.strip():
                try:
                    parsed_d = json.loads(raw_d)
                    if isinstance(parsed_d, (list, set)):
                        all_demonstrated.update(parsed_d)
                except (json.JSONDecodeError, ValueError):
                    pass

            raw_m = ev.get("missed_concepts")
            if isinstance(raw_m, (list, set)):
                all_missed.update(raw_m)
            elif isinstance(raw_m, str) and raw_m.strip():
                try:
                    parsed_m = json.loads(raw_m)
                    if isinstance(parsed_m, (list, set)):
                        all_missed.update(parsed_m)
                except (json.JSONDecodeError, ValueError):
                    pass

            history_points.append({
                "timestamp": ev.get("created_at"),
                "score": ev_score,
                "source": ev.get("source_type")
            })

        new_proficiency = round(total_weighted_score / total_weights, 1) if total_weights > 0 else bounded_score
        new_confidence = cls.calculate_confidence(len(all_evidence), sources_list, last_assessed_iso=now_iso)

        # Determine learning trend
        learning_trend = "STABLE"
        if len(history_points) >= 2:
            first_half = [p["score"] for p in history_points[:len(history_points)//2]]
            second_half = [p["score"] for p in history_points[len(history_points)//2:]]
            avg1 = sum(first_half) / len(first_half) if first_half else 0
            avg2 = sum(second_half) / len(second_half) if second_half else 0
            if avg2 - avg1 >= 5.0:
                learning_trend = "IMPROVING"
            elif avg1 - avg2 >= 5.0:
                learning_trend = "REGRESSING"

        # 3. Upsert into candidate_skill_profiles
        prof_res = supabase_client.table("candidate_skill_profiles").select("id").eq("user_id", user_id).eq("skill_id", skill_id).execute()
        existing_profile = prof_res.data[0] if (prof_res and prof_res.data) else None

        skill_profile_payload = {
            "user_id": user_id,
            "skill_id": skill_id,
            "proficiency": new_proficiency,
            "confidence": new_confidence,
            "evidence_count": len(all_evidence),
            "last_assessed": now_iso,
            "historical_proficiency": json.dumps(history_points),
            "learning_trend": learning_trend,
            "strong_concepts": json.dumps(list(all_demonstrated)[:10]),
            "growth_concepts": json.dumps(list(all_missed)[:10]),
            "updated_at": now_iso
        }

        if existing_profile:
            supabase_client.table("candidate_skill_profiles").update(skill_profile_payload).eq("id", existing_profile["id"]).execute()
        else:
            skill_profile_payload["id"] = str(uuid.uuid4())
            skill_profile_payload["created_at"] = now_iso
            supabase_client.table("candidate_skill_profiles").insert(skill_profile_payload).execute()

        conf_level = "VERIFIED" if new_confidence >= 0.80 else ("HIGH" if new_confidence >= 0.55 else ("MEDIUM" if new_confidence >= 0.35 else "LOW"))
        return {
            "skill_id": skill_id,
            "proficiency": new_proficiency,
            "confidence": new_confidence,
            "confidence_score": new_confidence,
            "confidence_level": conf_level,
            "evidence_count": len(all_evidence),
            "learning_trend": learning_trend,
            "trend": learning_trend
        }

    @classmethod
    def get_candidate_profile(cls, *args, **kwargs) -> Dict[str, Any]:
        """Returns dictionary of skill_id -> profile dict for assessed skills."""
        if len(args) == 2:
            supabase_client, user_id = args
        elif len(args) == 1:
            if isinstance(args[0], str):
                user_id = args[0]
                supabase_client = kwargs.get("supabase_client") or get_supabase_client()
            else:
                supabase_client = args[0]
                user_id = kwargs.get("user_id", "")
        else:
            user_id = kwargs.get("user_id", "")
            supabase_client = kwargs.get("supabase_client") or get_supabase_client()

        if not user_id:
            return {}

        res = supabase_client.table("candidate_skill_profiles").select("*").eq("user_id", user_id).execute()
        rows = res.data if (res and res.data) else []

        profiles: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            sid = r["skill_id"]
            meta = SkillTaxonomyService.get_skill(sid) or {}

            def _parse(v, default):
                if not v:
                    return default
                if isinstance(v, (list, dict)):
                    return v
                try:
                    return json.loads(v)
                except Exception:
                    return default

            conf_val = float(r.get("confidence", 0.0))
            conf_level = "VERIFIED" if conf_val >= 0.80 else ("HIGH" if conf_val >= 0.55 else ("MEDIUM" if conf_val >= 0.35 else "LOW"))
            prof_val = float(r.get("proficiency", 0.0))

            if prof_val >= 80.0:
                status_str = "MASTERED"
            elif prof_val >= 65.0:
                status_str = "PROFICIENT"
            elif prof_val >= 40.0:
                status_str = "DEVELOPING"
            else:
                status_str = "NEEDS_FOCUS"

            profiles[sid] = {
                "skill_id": sid,
                "name": meta.get("name", sid.replace("_", " ").title()),
                "category": meta.get("category", "General"),
                "difficulty": meta.get("difficulty", "Intermediate"),
                "proficiency": prof_val,
                "confidence": conf_val,
                "confidence_score": conf_val,
                "confidence_level": conf_level,
                "status": status_str,
                "evidence_count": int(r.get("evidence_count", 0)),
                "last_assessed": r.get("last_assessed"),
                "learning_trend": str(r.get("learning_trend", "STABLE")).upper(),
                "trend": str(r.get("learning_trend", "STABLE")).upper(),
                "historical_proficiency": _parse(r.get("historical_proficiency"), []),
                "strong_concepts": _parse(r.get("strong_concepts"), []),
                "growth_concepts": _parse(r.get("growth_concepts"), [])
            }

        return profiles

    @classmethod
    def get_candidate_profiles(cls, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        Returns list of all canonical skills (35+) with actual proficiency if assessed,
        or default 'NOT_ASSESSED' profile if unassessed.
        Guarantees the frontend Verified Skill Profiler displays the complete taxonomy.
        """
        p_dict = cls.get_candidate_profile(*args, **kwargs)
        all_skills = SkillTaxonomyService.get_all_skills()

        full_profiles = []
        for sk in all_skills:
            sid = sk["skill_id"]
            if sid in p_dict:
                full_profiles.append(p_dict[sid])
            else:
                # Canonical default for unassessed skill
                full_profiles.append({
                    "skill_id": sid,
                    "name": sk.get("name", sid.replace("_", " ").title()),
                    "category": sk.get("category", "General"),
                    "difficulty": sk.get("difficulty", "Intermediate"),
                    "proficiency": 0.0,
                    "confidence": 0.0,
                    "confidence_score": 0.0,
                    "confidence_level": "LOW",
                    "status": "NOT_ASSESSED",
                    "evidence_count": 0,
                    "last_assessed": None,
                    "learning_trend": "NOT_ASSESSED",
                    "trend": "NOT_ASSESSED",
                    "historical_proficiency": [],
                    "strong_concepts": [],
                    "growth_concepts": []
                })

        return full_profiles

    @classmethod
    def get_skill_evidence_history(cls, *args, **kwargs) -> List[Dict[str, Any]]:
        """Retrieves raw verifiable evidence rows for a specific candidate and skill."""
        if len(args) >= 3:
            supabase_client = args[0]
            user_id = args[1]
            skill_id = args[2]
        elif len(args) == 2:
            user_id = args[0]
            skill_id = args[1]
            supabase_client = kwargs.get("supabase_client") or get_supabase_client()
        else:
            user_id = kwargs.get("user_id", "")
            skill_id = kwargs.get("skill_id", "")
            supabase_client = kwargs.get("supabase_client") or get_supabase_client()

        limit = int(kwargs.get("limit", 20))

        if not user_id or not skill_id:
            return []
        res = supabase_client.table("skill_evidence").select("*").eq("user_id", user_id).eq("skill_id", skill_id).order("created_at", desc=True).limit(limit).execute()
        rows = res.data if (res and res.data) else []
        for r in rows:
            for k in ("demonstrated_concepts", "missed_concepts", "misconceptions"):
                if isinstance(r.get(k), str):
                    try:
                        r[k] = json.loads(r[k])
                    except Exception:
                        r[k] = []
        return rows

    @classmethod
    def get_candidate_proficiencies(cls, user_id: str, supabase_client: Any = None) -> Dict[str, float]:
        """Returns flat mapping of skill_id -> proficiency (0.0 to 100.0)."""
        profiles = cls.get_candidate_profile(user_id, supabase_client=supabase_client)
        return {s_id: float(p.get("proficiency", 0.0)) for s_id, p in profiles.items()}

    @classmethod
    def get_skill_gaps(cls, user_id: str, target_role: str, supabase_client: Any = None) -> List[Dict[str, Any]]:
        """Identifies skills where candidate proficiency is below the target role requirement."""
        from services.skill_taxonomy_service import SkillTaxonomyService
        role_reqs = SkillTaxonomyService.get_role_requirements(target_role)
        proficiencies = cls.get_candidate_proficiencies(user_id, supabase_client)
        gaps = []
        for req in role_reqs:
            s_id = req["skill_id"]
            current_prof = proficiencies.get(s_id, 0.0)
            target_prof = req.get("target_proficiency", 75.0)
            if current_prof < target_prof:
                gap_size = target_prof - current_prof
                gaps.append({
                    "skill_id": s_id,
                    "skill_name": s_id.replace("_", " ").title(),
                    "current_proficiency": current_prof,
                    "target_proficiency": target_prof,
                    "gap_size": gap_size,
                    "importance_weight": req.get("importance_weight", 1.0)
                })
        gaps.sort(key=lambda g: g["gap_size"] * g["importance_weight"], reverse=True)
        return gaps

    @classmethod
    def get_recurring_mistakes(cls, user_id: str, supabase_client: Any = None) -> List[str]:
        """Gathers recurring misconceptions from candidate evidence history."""
        client = supabase_client or get_supabase_client()
        try:
            res = client.table("skill_evidence").select("misconceptions").eq("user_id", user_id).limit(50).execute()
            if not res or not res.data:
                return []
            counts = {}
            for row in res.data:
                m_list = row.get("misconceptions") or []
                if isinstance(m_list, str):
                    try:
                        m_list = json.loads(m_list)
                    except Exception:
                        m_list = []
                for m in m_list:
                    if m and isinstance(m, str):
                        counts[m] = counts.get(m, 0) + 1
            sorted_m = sorted(counts.items(), key=lambda x: x[1], reverse=True)
            return [m for m, _ in sorted_m[:5]]
        except Exception:
            return []
