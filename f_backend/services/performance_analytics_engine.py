"""
PrepFly Performance Analytics Engine
Calculates real measurable performance improvements, statistical trend detection
(Improving, Stable, Declining, Insufficient Evidence), comparable baseline vs latest
snapshots, and synthesizes 100% grounded, factual coaching insights without LLM hallucinations.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import json
import uuid

from local_supabase import get_supabase_client
from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG
from services.skill_profiling_service import SkillProfilingService
from services.candidate_profile_service import CandidateProfileService


class PerformanceAnalyticsEngine:
    """Computes verified performance trajectories, snapshot deltas, and evidence-grounded insights."""

    TREND_IMPROVING = "Improving"
    TREND_STABLE = "Stable"
    TREND_DECLINING = "Declining"
    TREND_INSUFFICIENT = "Insufficient Evidence"

    DELTA_THRESHOLD = 5.0  # Percentage delta required to establish a meaningful trend

    @classmethod
    def get_full_improvement_report(
        cls,
        user_id: str,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Calculates the complete improvement tracking report:
        1. Current readiness vs baseline snapshot
        2. Statistical trend detection
        3. Dimension breakdown (accuracy, architecture, speed, communication)
        4. Factual, zero-hallucination coaching recommendations
        5. Historical trajectory snapshots
        """
        supabase = supabase_client or get_supabase_client()

        # 1. Fetch Candidate Skill Profiles
        skill_profiles = SkillProfilingService.get_candidate_profile(supabase, user_id)
        profile = CandidateProfileService.get_profile(supabase, user_id) or {}
        target_role = profile.get("target_role", "Software Development Engineer (General)")

        # 2. Get Snapshots
        snapshots = cls.get_snapshots(user_id, supabase_client=supabase)
        baseline_snap = next((s for s in snapshots if s.get("snapshot_type") == "baseline"), None)

        # If no snapshots exist in table, dynamically assemble evaluation checkpoints from evidence
        if not snapshots:
            snapshots = cls._gather_dynamic_checkpoints(user_id, supabase)

        # If no baseline exists but we have evidence, create initial baseline snapshot
        if not baseline_snap and skill_profiles:
            baseline_snap = cls.create_snapshot(user_id, snapshot_type="baseline", supabase_client=supabase)
            snapshots = cls.get_snapshots(user_id, supabase_client=supabase)

        # 3. Compute Current Metrics
        curr_overall = cls._compute_overall_readiness(skill_profiles, target_role)
        category_scores = cls._compute_category_scores(skill_profiles)

        # 4. Statistical Trend Detection
        trend_status, trend_slope, delta_pts = cls.detect_statistical_trend(snapshots, curr_overall)

        # 5. Comparable Dimension Deltas
        dimensions = cls._compute_dimension_deltas(baseline_snap, curr_overall, category_scores, skill_profiles)

        # 6. Synthesize Grounded Factual Insights
        insights = cls._generate_grounded_insights(
            user_id=user_id,
            skill_profiles=skill_profiles,
            curr_overall=curr_overall,
            baseline_snap=baseline_snap,
            trend_status=trend_status,
            dimensions=dimensions
        )

        obs_count = len(snapshots) + (1 if curr_overall > 0 and (not snapshots or snapshots[-1].get("overall_readiness") != curr_overall) else 0)

        return {
            "user_id": user_id,
            "target_role": target_role,
            "current_readiness": curr_overall,
            "trend": {
                "status": trend_status,
                "slope": round(trend_slope, 2),
                "delta_points": round(delta_pts, 1),
                "confidence": "HIGH" if obs_count >= 5 else ("MEDIUM" if obs_count >= 2 else "LOW"),
                "observations_count": obs_count
            },
            "dimensions": dimensions,
            "category_scores": category_scores,
            "baseline_comparison": {
                "has_baseline": baseline_snap is not None,
                "baseline_date": baseline_snap.get("created_at") if baseline_snap else None,
                "baseline_score": baseline_snap.get("overall_readiness") if baseline_snap else 0.0,
                "current_score": curr_overall,
                "total_improvement": round(curr_overall - (baseline_snap.get("overall_readiness", 0.0) if baseline_snap else 0.0), 1)
            },
            "insights": insights,
            "snapshots_history": [
                {
                    "id": s.get("id"),
                    "snapshot_type": s.get("snapshot_type"),
                    "overall_readiness": s.get("overall_readiness"),
                    "created_at": s.get("created_at")
                }
                for s in snapshots[:10]
            ]
        }

    @classmethod
    def _gather_dynamic_checkpoints(cls, user_id: str, supabase) -> List[Dict[str, Any]]:
        """Gathers chronological evaluation checkpoints from assessments, coding, and mock interviews."""
        checkpoints = []

        # Assessments
        ass_res = supabase.table("assessments").select("*").eq("user_id", user_id).eq("status", "completed").order("created_at", desc=False).execute()
        if ass_res and ass_res.data:
            for a in ass_res.data:
                checkpoints.append({
                    "id": a.get("id"),
                    "overall_readiness": float(a.get("score") or 0.0),
                    "created_at": a.get("completed_at") or a.get("created_at"),
                    "snapshot_type": "diagnostic" if a.get("assessment_type") == "diagnostic" else "periodic"
                })

        # Mock interviews
        sess_res = supabase.table("sessions").select("*").eq("user_id", user_id).order("created_at", desc=False).execute()
        if sess_res and sess_res.data:
            for s in sess_res.data:
                score = s.get("final_score")
                if score is not None:
                    checkpoints.append({
                        "id": s.get("session_id"),
                        "overall_readiness": float(score),
                        "created_at": s.get("created_at"),
                        "snapshot_type": "interview"
                    })

        # Sort chronologically
        checkpoints.sort(key=lambda c: c.get("created_at") or "")
        return checkpoints

    @classmethod
    def detect_statistical_trend(
        cls,
        snapshots: List[Dict[str, Any]],
        current_score: float
    ) -> Tuple[str, float, float]:
        """
        Determines statistical trend based on snapshot time-series:
        - Insufficient Evidence: < 2 comparable data points
        - Improving: net delta >= +5.0 and positive regression slope
        - Declining: net delta <= -5.0 and negative regression slope
        - Stable: variance within +/- 5.0
        """
        if not snapshots:
            return cls.TREND_INSUFFICIENT, 0.0, 0.0

        if snapshots and "created_at" in snapshots[0]:
            sorted_snaps = sorted(snapshots, key=lambda s: s.get("created_at", ""))
            scores = [float(s.get("overall_readiness", 0.0)) for s in sorted_snaps]
        else:
            scores = [float(s.get("overall_readiness", 0.0)) for s in snapshots]

        if not scores or (len(scores) == 1 and scores[0] == current_score):
            return cls.TREND_INSUFFICIENT, 0.0, 0.0

        if scores[-1] != current_score:
            scores.append(current_score)

        if len(scores) < 2:
            return cls.TREND_INSUFFICIENT, 0.0, 0.0

        # Linear regression slope: n * sum(xy) - sum(x)*sum(y) / (n * sum(x^2) - (sum(x))^2)
        n = len(scores)
        x_vals = list(range(n))
        sum_x = sum(x_vals)
        sum_y = sum(scores)
        sum_xy = sum(x * y for x, y in zip(x_vals, scores))
        sum_xx = sum(x * x for x in x_vals)

        denom = (n * sum_xx - (sum_x ** 2))
        slope = ((n * sum_xy) - (sum_x * sum_y)) / denom if denom != 0 else 0.0
        total_delta = scores[-1] - scores[0]

        if total_delta >= cls.DELTA_THRESHOLD and slope > 0.05:
            return cls.TREND_IMPROVING, slope, total_delta
        elif total_delta <= -cls.DELTA_THRESHOLD and slope < -0.05:
            return cls.TREND_DECLINING, slope, total_delta
        else:
            return cls.TREND_STABLE, slope, total_delta

    @classmethod
    def create_snapshot(
        cls,
        user_id: str,
        snapshot_type: str = "periodic",
        supabase_client=None
    ) -> Dict[str, Any]:
        """Captures and stores an immutable point-in-time performance snapshot."""
        supabase = supabase_client or get_supabase_client()
        skill_profiles = SkillProfilingService.get_candidate_profile(supabase, user_id)
        profile = CandidateProfileService.get_profile(supabase, user_id) or {}
        target_role = profile.get("target_role", "Software Development Engineer (General)")

        overall_readiness = cls._compute_overall_readiness(skill_profiles, target_role)
        category_scores = cls._compute_category_scores(skill_profiles)
        sample_counts = {
            "total_skills": len(skill_profiles),
            "evidence_items": sum(int(sp.get("evidence_count", 0)) for sp in skill_profiles.values())
        }

        snap_id = f"snap_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        row = {
            "id": snap_id,
            "user_id": user_id,
            "snapshot_type": snapshot_type,
            "overall_readiness": overall_readiness,
            "category_scores_json": json.dumps(category_scores),
            "sample_counts_json": json.dumps(sample_counts),
            "created_at": now_iso
        }
        supabase.table("performance_snapshots").insert(row).execute()
        return row

    @classmethod
    def get_snapshots(
        cls,
        user_id: str,
        limit: int = 20,
        supabase_client=None
    ) -> List[Dict[str, Any]]:
        """Retrieves user snapshots ordered by most recent first."""
        supabase = supabase_client or get_supabase_client()
        res = supabase.table("performance_snapshots").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        return res.data if (res and res.data) else []

    @classmethod
    def on_event(
        cls,
        supabase,
        user_id: str,
        event_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluates whether an incoming event warrants creating a new performance snapshot."""
        if event_type in ("assessment_completed", "interview_completed"):
            snap = cls.create_snapshot(user_id, snapshot_type="milestone", supabase_client=supabase)
            return {"snapshot_created": True, "snapshot_id": snap.get("id")}
        return {"snapshot_created": False}

    # =========================================================================
    # Internal Calculation Helpers
    # =========================================================================

    @classmethod
    def _compute_overall_readiness(cls, skill_profiles: Dict[str, Any], target_role: str) -> float:
        """Calculates role-weighted overall readiness score (0-100)."""
        role_weights = SkillTaxonomyService.get_role_weights(target_role)
        total_w = 0.0
        weighted_score = 0.0

        for sid, weight in role_weights.items():
            sp = skill_profiles.get(sid, {})
            prof = float(sp.get("proficiency", 0.0))
            weighted_score += prof * weight
            total_w += weight

        if total_w > 0:
            return round(weighted_score / total_w, 1)

        # Fallback to simple unweighted average across evaluated skills
        if skill_profiles:
            return round(sum(float(sp.get("proficiency", 0.0)) for sp in skill_profiles.values()) / len(skill_profiles), 1)
        return 0.0

    @classmethod
    def _compute_category_scores(cls, skill_profiles: Dict[str, Any]) -> Dict[str, float]:
        """Averages proficiencies per canonical skill taxonomy category."""
        cat_sums: Dict[str, float] = {}
        cat_counts: Dict[str, int] = {}

        for sid, skill in SKILL_CATALOG.items():
            category = skill.get("category", "General")
            sp = skill_profiles.get(sid)
            if sp:
                cat_sums[category] = cat_sums.get(category, 0.0) + float(sp.get("proficiency", 0.0))
                cat_counts[category] = cat_counts.get(category, 0) + 1

        category_scores: Dict[str, float] = {}
        for cat in SkillTaxonomyService.get_categories():
            count = cat_counts.get(cat, 0)
            category_scores[cat] = round(cat_sums[cat] / count, 1) if count > 0 else 0.0

        return category_scores

    @classmethod
    def _compute_dimension_deltas(
        cls,
        baseline_snap: Optional[Dict[str, Any]],
        curr_overall: float,
        curr_categories: Dict[str, float],
        skill_profiles: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Computes current vs baseline scores across core preparation dimensions."""
        base_cat_scores = {}
        if baseline_snap and baseline_snap.get("category_scores_json"):
            try:
                base_cat_scores = json.loads(baseline_snap["category_scores_json"])
            except Exception:
                base_cat_scores = {}

        dim_defs = [
            ("Technical Accuracy", "Data Structures and Algorithms", 70.0),
            ("System Design & Architecture", "System Design", 60.0),
            ("CS Fundamentals & Concurrency", "Computer Science Fundamentals", 65.0),
            ("Communication & Explanation", "Interview Skills", 75.0)
        ]

        dimensions = []
        for label, cat_name, benchmark in dim_defs:
            curr_val = curr_categories.get(cat_name, 0.0)
            base_val = float(base_cat_scores.get(cat_name, curr_val))
            delta = round(curr_val - base_val, 1)

            dimensions.append({
                "dimension": label,
                "category": cat_name,
                "current_score": curr_val,
                "baseline_score": base_val,
                "delta": delta,
                "industry_benchmark": benchmark,
                "benchmark_gap": round(curr_val - benchmark, 1),
                "status": "AHEAD" if curr_val >= benchmark else "IN_PROGRESS"
            })

        return dimensions

    @classmethod
    def _generate_grounded_insights(
        cls,
        user_id: str,
        skill_profiles: Dict[str, Any],
        curr_overall: float,
        baseline_snap: Optional[Dict[str, Any]],
        trend_status: str,
        dimensions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Produces 100% grounded, evidence-backed coaching insights.
        Zero LLM hallucinations: references verified numbers, deltas, and concrete skills.
        """
        insights = []

        # 1. Trend Milestone Insight
        base_score = float(baseline_snap.get("overall_readiness", 0.0)) if baseline_snap else curr_overall
        total_delta = round(curr_overall - base_score, 1)

        if trend_status == cls.TREND_IMPROVING:
            insights.append({
                "type": "TREND_POSITIVE",
                "priority": "HIGH",
                "title": f"Steady Improvement: +{total_delta} Readiness Gain",
                "message": (
                    f"Your overall readiness advanced from {base_score}% to {curr_overall}% (+{total_delta} points). "
                    "Consistent practice is translating into verified mastery."
                ),
                "action_type": "CONTINUE_MOMENTUM",
                "target_skill": None
            })
        elif trend_status == cls.TREND_DECLINING:
            insights.append({
                "type": "TREND_WARNING",
                "priority": "HIGH",
                "title": f"Performance Dip Detected ({total_delta} points)",
                "message": (
                    f"Your recent evaluations show a {abs(total_delta)} point drop compared to baseline. "
                    "Review failed test cases and misconceptions before advancing to harder difficulties."
                ),
                "action_type": "REMEDIAL_REVIEW",
                "target_skill": None
            })

        # 2. Critical Benchmark Gap Insight
        lagging_dim = min(dimensions, key=lambda d: d.get("benchmark_gap", 0.0)) if dimensions else None
        if lagging_dim and lagging_dim.get("benchmark_gap", 0.0) < 0:
            insights.append({
                "type": "BENCHMARK_GAP",
                "priority": "HIGH",
                "title": f"Priority Focus: {lagging_dim['dimension']}",
                "message": (
                    f"Current score in {lagging_dim['dimension']} is {lagging_dim['current_score']}%, "
                    f"which is {abs(lagging_dim['benchmark_gap'])} points below the {lagging_dim['industry_benchmark']}% industry benchmark. "
                    "Targeting this dimension will yield the highest interview score improvement."
                ),
                "action_type": "PRACTICE_DIMENSION",
                "target_skill": lagging_dim["category"]
            })

        # 3. Lowest Proficiency Skill Drill
        if skill_profiles:
            weakest_pair = sorted(skill_profiles.items(), key=lambda item: float(item[1].get("proficiency", 0.0)))
            if weakest_pair and float(weakest_pair[0][1].get("proficiency", 0.0)) < 65.0:
                weak_sid, weak_data = weakest_pair[0]
                sk_name = SKILL_CATALOG.get(weak_sid, {}).get("name", weak_sid.replace("_", " ").title())
                prof = float(weak_data.get("proficiency", 0.0))
                ev_count = int(weak_data.get("evidence_count", 0))

                insights.append({
                    "type": "SKILL_DRILL",
                    "priority": "MEDIUM",
                    "title": f"Targeted Practice: {sk_name}",
                    "message": (
                        f"Demonstrated proficiency in {sk_name} is {prof}% across {ev_count} evaluations. "
                        "Complete 2-3 focused exercises to elevate this skill to proficient standing."
                    ),
                    "action_type": "START_DRILL",
                    "target_skill": weak_sid
                })

        # Fallback if no specific triggers
        if not insights:
            insights.append({
                "type": "STABLE_PRACTICE",
                "priority": "LOW",
                "title": "On Track: Maintain Daily Consistency",
                "message": f"Your current readiness is stable at {curr_overall}%. Complete scheduled roadmap items to drive continuous improvement.",
                "action_type": "VIEW_ROADMAP",
                "target_skill": None
            })

        return insights
