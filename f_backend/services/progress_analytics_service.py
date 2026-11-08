"""
Progress Tracking & Improvement Analytics Engine for PrepFly Intelligence.
Aggregates candidate metrics, calculates decoupled role readiness, generates category radar data,
evaluates diagnostic baseline vs current proficiency comparisons with dual deltas,
and synthesizes grounded AI coaching insights.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import logging

from local_supabase import get_supabase_client
from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG
from services.skill_profiling_service import SkillProfilingService
from services.candidate_profile_service import CandidateProfileService
from services.assessment_service import AssessmentService
from services.revision_scheduler import RevisionScheduler
from services.cross_feature_engine import CrossFeatureEngine

logger = logging.getLogger("prepfly.intelligence.progress")


class ProgressAnalyticsService:
    """Computes comprehensive preparation analytics, baseline comparisons, and coaching recommendations."""

    @classmethod
    def get_dashboard_summary(cls, user_id: str) -> Dict[str, Any]:
        """
        Calculates the complete high-level preparation dashboard summary:
        - Readiness score (decoupled measured proficiency * coverage factor)
        - Skills mastered / proficient / developing / needs focus / unassessed
        - Multi-source completed study minutes (roadmap, Ava interviews, assessments, drills)
        - Spaced revision health & overdue count
        - Radar data across core competency dimensions with coverage
        - Diagnostic baseline vs current progress comparison with dual deltas
        """
        supabase = get_supabase_client()

        # 1. Candidate Profile & Target Role
        profile = CandidateProfileService.get_profile(user_id) or {}
        target_role = profile.get("target_role", "Software Development Engineer (General)")

        # 2. Candidate Skill Profiles
        skill_profiles = SkillProfilingService.get_candidate_profiles(user_id)
        profile_map = {sp["skill_id"]: sp for sp in skill_profiles}

        # 3. Role Requirements
        role_reqs = SkillTaxonomyService.get_role_requirements(target_role)

        # 4. Decoupled Role Readiness Calculation
        # Distinguish assessed skills (evidence_count >= 1 or status != "NOT_ASSESSED")
        # from unassessed curriculum requirements.
        assessed_weight = 0.0
        assessed_weighted_score = 0.0
        total_role_weight = 0.0

        mastered_count = 0
        proficient_count = 0
        developing_count = 0
        needs_focus_count = 0
        unassessed_count = 0

        for req in role_reqs:
            sk_id = req["skill_id"]
            weight = float(req.get("importance_weight", 1.0))
            total_role_weight += weight

            sp = profile_map.get(sk_id)
            ev_count = int(sp.get("evidence_count", 0)) if sp else 0
            status = sp.get("status", "NOT_ASSESSED") if sp else "NOT_ASSESSED"
            prof = float(sp.get("proficiency", 0.0)) if sp else 0.0

            if ev_count > 0 and status != "NOT_ASSESSED":
                assessed_weight += weight
                assessed_weighted_score += prof * weight

                if prof >= 80.0:
                    mastered_count += 1
                elif prof >= 65.0:
                    proficient_count += 1
                elif prof >= 40.0:
                    developing_count += 1
                else:
                    needs_focus_count += 1
            else:
                unassessed_count += 1

        coverage_ratio = (assessed_weight / total_role_weight) if total_role_weight > 0 else 0.0
        measured_proficiency = (assessed_weighted_score / assessed_weight) if assessed_weight > 0 else 0.0

        # Mathematical model: S_measured * (0.5 + 0.5 * Coverage)
        if assessed_weight > 0:
            overall_readiness = round(measured_proficiency * (0.5 + 0.5 * coverage_ratio), 1)
        else:
            overall_readiness = 0.0

        # 5. Multi-Source Study Minutes Calculation
        # Roadmap activities
        act_res = supabase.table("roadmap_activities").select("*").eq("user_id", user_id).execute()
        activities = act_res.data if (act_res and act_res.data) else []

        total_activities = len(activities)
        completed_activities = sum(1 for a in activities if a.get("status") == "COMPLETED")
        skipped_activities = sum(1 for a in activities if a.get("status") == "SKIPPED")
        roadmap_minutes_planned = sum(int(a.get("duration_minutes", 0)) for a in activities)
        roadmap_minutes_completed = sum(int(a.get("duration_minutes", 0)) for a in activities if a.get("status") == "COMPLETED")

        # Ava Mock Interviews: turn_count * 3 min or 25 min baseline
        sess_res = supabase.table("sessions").select("*").eq("user_id", user_id).execute()
        ava_sessions = sess_res.data if (sess_res and sess_res.data) else []
        ava_minutes = 0
        for s in ava_sessions:
            turns = int(s.get("turn_count") or 0)
            ava_minutes += max(15, turns * 3) if turns > 0 else 25

        # Assessments: 15 min per completed diagnostic / technical assessment
        ass_res = supabase.table("assessments").select("*").eq("user_id", user_id).eq("status", "completed").execute()
        ass_list = ass_res.data if (ass_res and ass_res.data) else []
        ass_minutes = len(ass_list) * 15

        # Retrieval drills: 5 min per completed attempt
        rev_res = supabase.table("revision_schedules").select("*").eq("user_id", user_id).execute()
        rev_list = rev_res.data if (rev_res and rev_res.data) else []
        rev_minutes = sum(int(r.get("retrieval_attempts", 0)) * 5 for r in rev_list)

        total_minutes_completed = roadmap_minutes_completed + ava_minutes + ass_minutes + rev_minutes
        total_minutes_planned = max(total_minutes_completed, roadmap_minutes_planned)

        # 6. Revision Health
        due_revisions = RevisionScheduler.get_due_revisions(user_id)
        all_revisions = RevisionScheduler.get_all_schedules(user_id)
        revision_mastered = sum(1 for r in all_revisions if r.get("interval_stage", 1) >= 4 and r.get("status") == "COMPLETED")

        # 7. Radar Chart Competency Pillars (4 Core Dashboard Dimensions)
        categories = [
            SkillTaxonomyService.CAT_DSA,
            SkillTaxonomyService.CAT_CS,
            SkillTaxonomyService.CAT_SYSTEM_DESIGN,
            SkillTaxonomyService.CAT_INTERVIEW_SKILLS
        ]
        radar_data = []

        for cat in categories:
            cat_skills = [s_id for s_id, s_info in SKILL_CATALOG.items() if s_info.get("category") == cat]
            total_cat_count = len(cat_skills)

            assessed_in_cat = [
                s for s in cat_skills
                if s in profile_map and int(profile_map[s].get("evidence_count", 0)) > 0
            ]
            if assessed_in_cat:
                cat_prof_sum = sum(float(profile_map[s].get("proficiency", 0.0)) for s in assessed_in_cat)
                avg_prof = round(cat_prof_sum / len(assessed_in_cat), 1)
            else:
                avg_prof = 0.0

            coverage_pct = round((len(assessed_in_cat) / max(1, total_cat_count)) * 100.0, 1)

            radar_data.append({
                "dimension": cat,
                "score": avg_prof,
                "coverage_percentage": coverage_pct,
                "assessed_count": len(assessed_in_cat),
                "total_count": total_cat_count,
                "max": 100
            })

        # 8. Diagnostic Baseline vs Current Comparison (Dual Deltas)
        baseline_comparison = cls._compute_baseline_comparison(user_id, skill_profiles)

        return {
            "overall_readiness": overall_readiness,
            "measured_proficiency": round(measured_proficiency, 1),
            "curriculum_coverage": round(coverage_ratio * 100.0, 1),
            "target_role": target_role,
            "target_company": profile.get("target_company", "Top Tech"),
            "target_date": profile.get("target_date"),
            "study_metrics": {
                "total_activities": total_activities,
                "completed_activities": completed_activities,
                "skipped_activities": skipped_activities,
                "completion_percentage": round((completed_activities / total_activities * 100), 1) if total_activities > 0 else 0.0,
                "total_minutes_planned": total_minutes_planned,
                "total_minutes_completed": total_minutes_completed,
                "roadmap_minutes": roadmap_minutes_completed,
                "mock_interview_minutes": ava_minutes,
                "assessment_minutes": ass_minutes,
                "drill_minutes": rev_minutes
            },
            "skill_distribution": {
                "mastered": mastered_count,
                "proficient": proficient_count,
                "developing": developing_count,
                "needs_focus": needs_focus_count,
                "unassessed": unassessed_count,
                "total_tracked": len(role_reqs),
                "coverage_percentage": round(coverage_ratio * 100.0, 1)
            },
            "revision_health": {
                "overdue_count": len(due_revisions),
                "total_scheduled": len(all_revisions),
                "retention_mastered": revision_mastered
            },
            "radar_data": radar_data,
            "baseline_comparison": baseline_comparison
        }

    @classmethod
    def _compute_baseline_comparison(
        cls,
        user_id: str,
        current_profiles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compares immutable initial diagnostic assessment attempt against current proficiencies.
        Returns percentage points delta (pp) and relative improvement percentage (%).
        """
        supabase = get_supabase_client()
        res = supabase.table("assessments").select("*").eq("user_id", user_id).eq("status", "completed").order("created_at", desc=False).execute()
        attempts = res.data if (res and res.data) else []

        if not attempts:
            return {
                "has_baseline": False,
                "message": "No diagnostic assessment completed yet."
            }

        initial_attempt = attempts[0]
        initial_score = float(initial_attempt.get("score") or initial_attempt.get("overall_score") or 0.0)
        initial_date = initial_attempt.get("completed_at") or initial_attempt.get("created_at") or ""
        assessment_id = initial_attempt.get("id") or initial_attempt.get("assessment_id") or ""

        # Current average proficiency across assessed skills
        assessed_profiles = [p for p in current_profiles if int(p.get("evidence_count", 0)) > 0]
        if assessed_profiles:
            curr_avg = round(sum(float(p.get("proficiency", 0.0)) for p in assessed_profiles) / len(assessed_profiles), 1)
        elif current_profiles:
            curr_avg = round(sum(float(p.get("proficiency", 0.0)) for p in current_profiles) / len(current_profiles), 1)
        else:
            curr_avg = initial_score

        delta_pp = round(curr_avg - initial_score, 1)
        relative_improvement_pct = round(((curr_avg - initial_score) / max(1.0, initial_score)) * 100.0, 1)

        # Concept-level deltas
        init_breakdown = initial_attempt.get("concept_breakdown") or {}
        if isinstance(init_breakdown, str):
            try:
                init_breakdown = json.loads(init_breakdown)
            except Exception:
                init_breakdown = {}

        skill_deltas = []
        for sk_id, init_val in init_breakdown.items():
            curr_p = next((p for p in current_profiles if p["skill_id"] == sk_id), None)
            curr_val = float(curr_p["proficiency"]) if curr_p else float(init_val)
            cat_entry = SKILL_CATALOG.get(sk_id, {})
            concept_init = float(init_val)
            c_delta_pp = round(curr_val - concept_init, 1)
            c_rel_pct = round(((curr_val - concept_init) / max(1.0, concept_init)) * 100.0, 1)

            skill_deltas.append({
                "skill_id": sk_id,
                "skill_name": cat_entry.get("name", sk_id.replace("_", " ").title()),
                "initial_score": concept_init,
                "current_score": curr_val,
                "delta": c_delta_pp,
                "delta_pp": c_delta_pp,
                "relative_improvement_pct": c_rel_pct
            })

        return {
            "has_baseline": True,
            "is_immutable": True,
            "initial_score": initial_score,
            "initial_date": initial_date,
            "assessment_id": assessment_id,
            "current_score": curr_avg,
            "overall_delta": delta_pp,
            "overall_delta_pp": delta_pp,
            "relative_improvement_pct": relative_improvement_pct,
            "skill_deltas": skill_deltas
        }

    @classmethod
    def get_grounded_coaching_insights(cls, user_id: str) -> List[Dict[str, Any]]:
        """
        Produces actionable, evidence-grounded coaching insights tailored to candidate performance.
        Synthesizes cross-feature multi-source weaknesses, due spaced revisions, regression warnings,
        and demonstrated strengths. Grounded with strict zero-hallucination deterministic fallbacks.
        """
        profiles = SkillProfilingService.get_candidate_profiles(user_id)
        due_revisions = RevisionScheduler.get_due_revisions(user_id)
        cross_weaknesses = CrossFeatureEngine.detect_cross_feature_weaknesses(user_id)

        # Assessed skills only for ranking
        assessed_profiles = [p for p in profiles if int(p.get("evidence_count", 0)) > 0]
        
        # Skills with regressing trend
        regressing = [p for p in assessed_profiles if p.get("trend") == "REGRESSING" or p.get("learning_trend") == "REGRESSING"]

        # Strengths
        strengths = [p for p in assessed_profiles if float(p.get("proficiency", 0.0)) >= 80.0]

        insights = []

        # 1. Top Cross-Feature Weakness (Highest Priority)
        if cross_weaknesses:
            top_cw = cross_weaknesses[0]
            sources_desc = ", ".join(f"{s['source'].replace('_', ' ')} ({s['average_score']}%)" for s in top_cw.get("failing_sources", []))
            insights.append({
                "type": "CROSS_FEATURE_WEAKNESS",
                "priority": "HIGH",
                "title": f"Systemic Deficit: {top_cw['skill_name']}",
                "message": (
                    f"Consistently flagged across multiple modules: {sources_desc}. "
                    f"Deficit to benchmark is {top_cw.get('deficit', 0)} points. {top_cw.get('remedial_recommendation', '')}"
                ),
                "action_type": "PRACTICE_DRILL",
                "target_skill": top_cw["skill_id"]
            })
        elif assessed_profiles:
            # Lowest assessed proficiency
            weakest = sorted(assessed_profiles, key=lambda x: (float(x.get("proficiency", 0.0)), float(x.get("confidence", 0.0))))[:1]
            if weakest and float(weakest[0].get("proficiency", 0.0)) < 60.0:
                top_w = weakest[0]
                cat_entry = SKILL_CATALOG.get(top_w["skill_id"], {})
                name = cat_entry.get("name", top_w["skill_id"])
                prof = float(top_w.get("proficiency", 0.0))
                insights.append({
                    "type": "WEAKNESS_ALERT",
                    "priority": "HIGH",
                    "title": f"Targeted Drill Needed: {name}",
                    "message": (
                        f"Your current proficiency in {name} is {prof}%. "
                        "Focusing 30 minutes on core foundational patterns and conceptual invariants will rapidly unlock downstream topics."
                    ),
                    "action_type": "PRACTICE_DRILL",
                    "target_skill": top_w["skill_id"]
                })

        # 2. Spaced Revision Reminder
        if due_revisions:
            first_due = due_revisions[0]
            insights.append({
                "type": "SPACED_REVISION",
                "priority": "HIGH",
                "title": f"Spaced Revision Due: {first_due['skill_name']}",
                "message": (
                    f"You have {len(due_revisions)} retrieval drill(s) due today. "
                    f"Completing a 5-minute recall session for {first_due['skill_name']} will reinforce long-term memory retention."
                ),
                "action_type": "START_REVISION",
                "target_skill": first_due["skill_id"]
            })

        # 3. Regression Safeguard
        if regressing:
            target_reg = regressing[0]
            cat_entry = SKILL_CATALOG.get(target_reg["skill_id"], {})
            name = cat_entry.get("name", target_reg["skill_id"])
            insights.append({
                "type": "REGRESSION_WARNING",
                "priority": "MEDIUM",
                "title": f"Performance Drift Detected: {name}",
                "message": (
                    f"Recent evaluations in {name} scored lower than historical baseline. "
                    "Review previous test cases and boundary conditions to restore stability."
                ),
                "action_type": "REVIEW_MISTAKES",
                "target_skill": target_reg["skill_id"]
            })

        # 4. Strength Reinforcement
        if strengths:
            top_s = strengths[0]
            cat_entry = SKILL_CATALOG.get(top_s["skill_id"], {})
            name = cat_entry.get("name", top_s["skill_id"])
            insights.append({
                "type": "STRENGTH_HIGHLIGHT",
                "priority": "LOW",
                "title": f"Strong Domain: {name}",
                "message": (
                    f"You have demonstrated {round(float(top_s.get('proficiency', 0.0)))}% proficiency in {name}. "
                    "This is an asset for technical rounds; maintain it with periodic mock interview questions."
                ),
                "action_type": "MOCK_INTERVIEW",
                "target_skill": top_s["skill_id"]
            })

        # Default fallback if profile is completely fresh
        if not insights:
            insights.append({
                "type": "GET_STARTED",
                "priority": "HIGH",
                "title": "Complete Your Diagnostic Assessment",
                "message": "Take the 5-question adaptive diagnostic assessment to calibrate your baseline proficiency and generate your custom preparation roadmap.",
                "action_type": "TAKE_ASSESSMENT",
                "target_skill": None
            })

        return insights

