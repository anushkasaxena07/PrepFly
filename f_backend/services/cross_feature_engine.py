"""
Cross-Feature Weakness Detection & Integration Engine for PrepFly Intelligence.
Connects learning signals across Ava mock interviews, coding submissions, and assessments
to canonical skill IDs in the master taxonomy.
"""

from typing import Dict, List, Optional, Any
import json
from local_supabase import get_supabase_client
from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG
from services.skill_profiling_service import SkillProfilingService

class CrossFeatureEngine:
    """Extracts verifiable performance signals across PrepFly modules and updates skill profiles."""

    @classmethod
    def process_coding_submission(
        cls,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extracts skill evidence from a coding playground / assessment submission.
        Maps problem category & complexity results to canonical skill IDs.
        """
        if len(args) >= 6 and not isinstance(args[0], str):
            supabase_client = args[0]
            user_id = args[1]
            problem_id = args[2]
            language = args[3]
            passed = args[4]
            total = args[5]
            time_complexity = args[6] if len(args) > 6 else kwargs.get("time_complexity", "-")
            space_complexity = args[7] if len(args) > 7 else kwargs.get("space_complexity", "-")
        else:
            supabase_client = kwargs.get("supabase_client") or get_supabase_client()
            user_id = args[0] if args else kwargs.get("user_id", "")
            problem_id = args[1] if len(args) > 1 else kwargs.get("problem_id", "")
            language = args[2] if len(args) > 2 else kwargs.get("language", "python")
            passed = kwargs.get("passed", kwargs.get("passed_tests", 0))
            total = kwargs.get("total", kwargs.get("total_tests", 1))
            time_complexity = kwargs.get("time_complexity", "-")
            space_complexity = kwargs.get("space_complexity", "-")

        if not user_id or not problem_id:
            return {"success": False, "recorded_evidence": []}

        # 1. Fetch problem metadata from coding_problems
        prob_res = supabase_client.table("coding_problems").select("*").eq("problem_id", problem_id).execute()
        prob = prob_res.data[0] if (prob_res and prob_res.data) else {}
        
        category = prob.get("category", "")
        title = prob.get("title", problem_id)
        desc = prob.get("description", "")

        # 2. Map problem text & category to canonical skills
        associated_skills = SkillTaxonomyService.map_text_to_skills(f"{problem_id} {title} {category} {desc}")
        if not associated_skills:
            associated_skills = ["dsa_arrays"]

        # Calculate score (0-100) based on test case pass ratio
        ratio = (passed / max(1, total)) if total > 0 else 0.0
        score = round(ratio * 100.0, 1)

        demonstrated = []
        missed = []
        if score >= 70.0:
            demonstrated.append(f"Passed {passed}/{total} test cases in {language}")
        else:
            missed.append(f"Failed {total - passed}/{total} test cases in {language}")

        recorded_ev = []
        for sid in associated_skills:
            ev = SkillProfilingService.record_evidence(
                supabase_client=supabase_client,
                user_id=user_id,
                skill_id=sid,
                source_type="coding_submission",
                source_id=problem_id,
                score=score,
                demonstrated_concepts=demonstrated,
                missed_concepts=missed,
                notes=f"Solved {title} ({problem_id}) with {language}. Pass ratio: {passed}/{total}.",
                rubric_version="v1"
            )
            recorded_ev.append(ev)

        # 3. Evaluate complexity analysis skill if provided
        if time_complexity and time_complexity != "-":
            comp_score = 90.0 if "o(" in time_complexity.lower() else 50.0
            comp_ev = SkillProfilingService.record_evidence(
                supabase_client=supabase_client,
                user_id=user_id,
                skill_id="soft_complexity_analysis",
                source_type="coding_submission",
                source_id=problem_id,
                score=comp_score,
                demonstrated_concepts=[f"Time: {time_complexity}", f"Space: {space_complexity}"] if comp_score >= 70.0 else [],
                missed_concepts=[f"Inaccurate complexity estimation: {time_complexity}"] if comp_score < 70.0 else [],
                notes=f"Complexity analysis on {problem_id}: Time={time_complexity}, Space={space_complexity}",
                rubric_version="v1"
            )
            recorded_ev.append(comp_ev)

        return {
            "success": True,
            "recorded_evidence": recorded_ev
        }

    @classmethod
    def process_ava_interview_session(
        cls,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extracts multi-dimensional skill evidence from a completed Ava mock interview.
        Maps interview responses, technical explanations, and communication scores to canonical skill IDs.
        """
        if len(args) >= 5 and not isinstance(args[0], str):
            supabase_client = args[0]
            user_id = args[1]
            session_id = args[2]
            feedbacks_json = args[3]
            final_score = args[4]
            category = args[5] if len(args) > 5 else kwargs.get("category", "")
        else:
            supabase_client = kwargs.get("supabase_client") or get_supabase_client()
            user_id = args[0] if args else kwargs.get("user_id", "")
            session_id = args[1] if len(args) > 1 else kwargs.get("session_id", "")
            final_report = kwargs.get("final_report") or {}
            final_score = float(final_report.get("overall_score") or kwargs.get("final_score", 70.0))
            feedbacks_json = kwargs.get("feedbacks") or final_report.get("feedbacks", [])
            category = kwargs.get("category", "")

        if not user_id or not session_id:
            return {"success": False, "recorded_evidence": []}

        # Parse feedbacks
        feedbacks = []
        if isinstance(feedbacks_json, str):
            try:
                feedbacks = json.loads(feedbacks_json)
            except Exception:
                feedbacks = []
        elif isinstance(feedbacks_json, list):
            feedbacks = feedbacks_json

        recorded_ev = []

        # 1. Ingest overall communication & problem formulation evidence
        comm_score = min(100.0, max(0.0, final_score))
        comm_ev = SkillProfilingService.record_evidence(
            supabase_client=supabase_client,
            user_id=user_id,
            skill_id="soft_communication",
            source_type="ava_interview",
            source_id=session_id,
            score=comm_score,
            demonstrated_concepts=["Verbal explanation", "Live interview interaction"] if comm_score >= 65.0 else [],
            missed_concepts=["Clarity and conciseness under live interview conditions"] if comm_score < 65.0 else [],
            notes=f"Ava Mock Interview session {session_id} communication rating.",
            rubric_version="v1"
        )
        recorded_ev.append(comm_ev)

        # 2. Extract technical skill signals from questions & candidate responses
        for fb in feedbacks:
            q_text = fb.get("question", "") if isinstance(fb, dict) else str(fb)
            f_text = fb.get("feedback", "") if isinstance(fb, dict) else ""
            item_score = float(fb.get("score", final_score)) if isinstance(fb, dict) else final_score

            matched_skills = SkillTaxonomyService.map_text_to_skills(f"{q_text} {f_text} {category}")
            for sid in matched_skills:
                ev = SkillProfilingService.record_evidence(
                    supabase_client=supabase_client,
                    user_id=user_id,
                    skill_id=sid,
                    source_type="ava_interview",
                    source_id=session_id,
                    score=item_score,
                    demonstrated_concepts=[f"Addressed: {q_text[:80]}..."] if item_score >= 65.0 else [],
                    missed_concepts=[f"Needs review: {f_text[:80]}..."] if item_score < 65.0 else [],
                    notes=f"Interview question feedback: {f_text[:120]}",
                    rubric_version="v1"
                )
                recorded_ev.append(ev)

        return {
            "success": True,
            "recorded_evidence": recorded_ev
        }

    @classmethod
    def detect_cross_feature_weaknesses(
        cls,
        *args,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Identifies skills that exhibit consistent weakness (< 60% average across >= 2 distinct
        evidence sources, or >= 2 repeated attempts with average < 55% in a single source).
        Prioritizes deficits to 75% target weighted by role importance and prerequisites.
        """
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
            return []

        # Query all evidence
        ev_res = supabase_client.table("skill_evidence").select("*").eq("user_id", user_id).execute()
        evidence_items = ev_res.data if (ev_res and ev_res.data) else []

        by_skill: Dict[str, Dict[str, List[float]]] = {}
        for ev in evidence_items:
            sid = ev["skill_id"]
            src = ev["source_type"]
            score = float(ev.get("score", 0.0))

            if sid not in by_skill:
                by_skill[sid] = {}
            if src not in by_skill[sid]:
                by_skill[sid][src] = []
            by_skill[sid][src].append(score)

        # Get role requirements for weighting
        try:
            from services.candidate_profile_service import CandidateProfileService
            cand_profile = CandidateProfileService.get_profile(user_id) or {}
            target_role = cand_profile.get("target_role", "Software Development Engineer (General)")
            role_reqs = SkillTaxonomyService.get_role_requirements(target_role)
            role_weights = {r["skill_id"]: float(r.get("importance_weight", 1.0)) for r in role_reqs}
        except Exception:
            role_weights = {}

        weaknesses = []
        for sid, sources in by_skill.items():
            failing_sources = []
            total_fail_attempts = 0
            fail_score_sum = 0.0

            for src, scores in sources.items():
                avg = sum(scores) / len(scores)
                if avg < 60.0:
                    failing_sources.append({
                        "source": src,
                        "average_score": round(avg, 1),
                        "attempts": len(scores)
                    })
                    total_fail_attempts += len(scores)
                    fail_score_sum += sum(scores)

            # Rule: Fail in >= 2 distinct sources OR >= 2 attempts with avg < 55 in single source
            is_confirmed_weakness = False
            if len(failing_sources) >= 2:
                is_confirmed_weakness = True
            elif len(failing_sources) == 1 and failing_sources[0]["attempts"] >= 2 and failing_sources[0]["average_score"] < 55.0:
                is_confirmed_weakness = True

            if is_confirmed_weakness and total_fail_attempts > 0:
                skill_meta = SkillTaxonomyService.get_skill(sid) or {}
                skill_name = skill_meta.get("name", sid.replace("_", " ").title())
                category = skill_meta.get("category", "General")
                overall_fail_avg = round(fail_score_sum / total_fail_attempts, 1)
                
                # Deficit to target benchmark (75.0%)
                target_score = 75.0
                deficit = round(max(0.0, target_score - overall_fail_avg), 1)
                
                role_wt = role_weights.get(sid, 1.0)
                prereqs = skill_meta.get("prerequisites", [])
                priority_score = round(deficit * role_wt * (1.0 + 0.25 * len(prereqs)), 2)

                # Grounded remediation guidance
                if prereqs:
                    prereq_names = [SkillTaxonomyService.get_skill(p).get("name", p) for p in prereqs if SkillTaxonomyService.get_skill(p)]
                    prereq_str = ", ".join(prereq_names) if prereq_names else ", ".join(prereqs)
                    remedial = f"Strengthen prerequisite concepts ({prereq_str}) first, then complete targeted practice drills on {skill_name} before live mock interviews."
                else:
                    remedial = f"Review fundamental patterns in {skill_name} and complete 5-minute retrieval drills before taking live mock interviews."

                weaknesses.append({
                    "skill_id": sid,
                    "skill_name": skill_name,
                    "category": category,
                    "failing_sources": failing_sources,
                    "average_score": overall_fail_avg,
                    "target_score": target_score,
                    "deficit": deficit,
                    "priority_score": priority_score,
                    "remedial_recommendation": remedial
                })

        # Sort by priority score descending
        weaknesses.sort(key=lambda w: w["priority_score"], reverse=True)
        return weaknesses
