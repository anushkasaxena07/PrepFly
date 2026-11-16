"""
PREPFLY SCORING ENGINE (Section 5 & Section 6)
==============================================
Pure mathematical scoring engine complying with the Full Build Specification.
Follows Golden Rules:
1. The LLM writes content. Code computes numbers.
2. One source of truth for readiness, proficiency, coverage, and confidence.
3. No fake mastery: only graded evidence changes proficiency.
4. No unassessed skill is ever called a weakness (NOT_ASSESSED != gap).
5. All outputs are in 0-100 and rounded to 1 decimal only at display time.
"""

from typing import Dict, List, Optional, Any, Tuple, Union, Set
from datetime import datetime, date, timezone
import math
import logging

logger = logging.getLogger("prepfly.scoring_engine")

# -----------------------------------------------------------------------------
# CONSTANTS & CONFIGURATION
# -----------------------------------------------------------------------------

RECENCY_HALF_LIFE_DAYS = 90.0

DIFFICULTY_WEIGHTS = {
    "EASY": 0.8,
    "MEDIUM": 1.0,
    "HARD": 1.3
}

TYPE_WEIGHTS = {
    "MCQ": 0.7,
    "SHORT_ANSWER": 1.0,
    "SCENARIO": 1.1,
    "CODE": 1.2,
    "MOCK_INTERVIEW": 1.2,
    "PRACTICE_ASSIGNMENT": 1.0
}

TIER_WEIGHTS = {
    "MANDATORY": 1.5,
    "PREFERRED": 1.0,
    "SUPPORTING": 0.7
}

STATUS_NOT_ASSESSED = "NOT_ASSESSED"
STATUS_LOW_EVIDENCE = "LOW_EVIDENCE"
STATUS_VERIFIED_GAP = "VERIFIED_GAP"
STATUS_DEVELOPING = "DEVELOPING"
STATUS_VERIFIED_STRONG = "VERIFIED_STRONG"

PILLAR_NOT_ASSESSED = "NOT_ASSESSED"
PILLAR_PARTIALLY_ASSESSED = "PARTIALLY_ASSESSED"
PILLAR_ASSESSED = "ASSESSED"

TREND_IMPROVING = "IMPROVING"
TREND_FLAT = "FLAT"
TREND_DECLINING = "DECLINING"
TREND_NOT_ENOUGH_DATA = "Not enough data yet"


# -----------------------------------------------------------------------------
# 5.1 EVIDENCE WEIGHTING
# -----------------------------------------------------------------------------

def calculate_recency_weight(age_in_days: float) -> float:
    """
    Computes 90-day half-life decay: recencyWeight(e) = 0.5 ^ (ageInDays / 90).
    Non-negative age is clamped.
    """
    safe_age = max(0.0, float(age_in_days if age_in_days is not None else 0.0))
    return float(math.pow(0.5, safe_age / RECENCY_HALF_LIFE_DAYS))


def get_difficulty_weight(difficulty: Optional[str]) -> float:
    """Returns difficulty multiplier: EASY=0.8, MEDIUM=1.0, HARD=1.3."""
    key = str(difficulty or "MEDIUM").upper().strip()
    return float(DIFFICULTY_WEIGHTS.get(key, 1.0))


def get_type_weight(evidence_type: Optional[str]) -> float:
    """
    Returns question/evidence type multiplier:
    MCQ=0.7, SHORT_ANSWER=1.0, SCENARIO=1.1, CODE=1.2, MOCK_INTERVIEW=1.2, PRACTICE_ASSIGNMENT=1.0.
    """
    key = str(evidence_type or "SHORT_ANSWER").upper().strip()
    return float(TYPE_WEIGHTS.get(key, 1.0))


def calculate_evidence_weight(age_in_days: float = 0.0, difficulty: str = "MEDIUM", evidence_type: str = "SHORT_ANSWER") -> float:
    """
    Computes combined evidence weight:
    w(e) = recencyWeight * difficultyWeight * typeWeight
    """
    rw = calculate_recency_weight(age_in_days)
    dw = get_difficulty_weight(difficulty)
    tw = get_type_weight(evidence_type)
    return float(rw * dw * tw)


# -----------------------------------------------------------------------------
# 5.2 SKILL PROFICIENCY
# -----------------------------------------------------------------------------

def calculate_skill_proficiency(evidence_items: List[Dict[str, Any]]) -> Tuple[Optional[float], float]:
    """
    Computes skill proficiency from attempted evidence items only:
    P_skill = Σ(score_e × w_e) / Σ(w_e)
    
    Returns (P_skill, sum_weights).
    If there is no attempted evidence -> (None, 0.0).
    """
    if not evidence_items:
        return (None, 0.0)

    total_weighted_score = 0.0
    total_weights = 0.0

    for item in evidence_items:
        raw_score = item.get("score")
        if raw_score is None:
            continue
        try:
            score_val = float(raw_score)
        except (ValueError, TypeError):
            continue

        # Check explicit unattempted flag if present
        if item.get("is_attempted") is False or item.get("skipped") is True:
            continue

        age_days = float(item.get("age_in_days", 0.0) or 0.0)
        diff = str(item.get("difficulty", "MEDIUM"))
        ev_type = str(item.get("evidence_type", item.get("type", "SHORT_ANSWER")))

        w = calculate_evidence_weight(age_days, diff, ev_type)
        if w > 0:
            total_weighted_score += (score_val * w)
            total_weights += w

    if total_weights <= 0.0:
        return (None, 0.0)

    p_skill = total_weighted_score / total_weights
    return (float(p_skill), float(total_weights))


# -----------------------------------------------------------------------------
# 5.3 SKILL CONFIDENCE
# -----------------------------------------------------------------------------

def calculate_skill_confidence(
    sum_weights: float,
    subskills_tested: Union[int, Set[str], List[str]],
    total_subskills_count: int = 3
) -> float:
    """
    Computes skill confidence (how much we trust P_skill):
    evidenceFactor  = min(1.0, Σ(w_e) / 3.0)
    diversityFactor = min(1.0, distinctSubskillsTested / min(3, subskillCount))
    C_skill         = 0.7 × evidenceFactor + 0.3 × diversityFactor
    
    Range: [0.0, 1.0].
    """
    evidence_factor = min(1.0, max(0.0, float(sum_weights)) / 3.0)

    if isinstance(subskills_tested, (set, list, tuple)):
        distinct_tested = len(set(subskills_tested))
    else:
        try:
            distinct_tested = max(0, int(subskills_tested or 0))
        except (ValueError, TypeError):
            distinct_tested = 0

    denom = min(3, max(1, int(total_subskills_count or 3)))
    diversity_factor = min(1.0, distinct_tested / denom)

    c_skill = (0.7 * evidence_factor) + (0.3 * diversity_factor)
    return float(min(1.0, max(0.0, c_skill)))


# -----------------------------------------------------------------------------
# 5.4 SKILL STATUS
# -----------------------------------------------------------------------------

def classify_skill_status(proficiency: Optional[float], confidence: float) -> str:
    """
    Determines status following exact spec:
    - NOT_ASSESSED: no attempted evidence (proficiency is None)
    - LOW_EVIDENCE: has evidence but C_skill < 0.4 (provisional, never labeled as gap)
    - VERIFIED_GAP: P_skill < 60 AND C_skill ≥ 0.4
    - DEVELOPING: 60 ≤ P_skill < 85 AND C_skill ≥ 0.4
    - VERIFIED_STRONG: P_skill ≥ 85 AND C_skill ≥ 0.4
    """
    if proficiency is None:
        return STATUS_NOT_ASSESSED

    conf = float(confidence if confidence is not None else 0.0)
    if conf < 0.4:
        return STATUS_LOW_EVIDENCE

    p = float(proficiency)
    if p < 60.0:
        return STATUS_VERIFIED_GAP
    elif p < 85.0:
        return STATUS_DEVELOPING
    else:
        return STATUS_VERIFIED_STRONG


# -----------------------------------------------------------------------------
# 5.5 PILLAR AGGREGATION
# -----------------------------------------------------------------------------

def aggregate_pillar(skills: List[Dict[str, Any]], pillar_name: str = "Core Domain") -> Dict[str, Any]:
    """
    Computes pillar-level proficiency and coverage:
    - pillarProficiency = tier-weighted mean of assessed skills in that pillar
    - pillarCoverage = assessed skills / total skills (formatted as e.g. "2/4")
    - Pillar status: NOT_ASSESSED (0 assessed), PARTIALLY_ASSESSED (< 50% skills assessed), ASSESSED
    """
    total_count = len(skills)
    assessed = [s for s in skills if s.get("proficiency") is not None]
    assessed_count = len(assessed)

    coverage_ratio = (assessed_count / total_count) if total_count > 0 else 0.0

    if assessed_count == 0:
        return {
            "name": pillar_name,
            "proficiency": None,
            "assessed_count": 0,
            "total_count": total_count,
            "coverage_display": f"0/{total_count}",
            "coverage_ratio": 0.0,
            "status": PILLAR_NOT_ASSESSED
        }

    tier_weighted_sum = 0.0
    tier_weight_sum = 0.0

    for s in assessed:
        t_key = str(s.get("tier", "PREFERRED")).upper().strip()
        tw = float(TIER_WEIGHTS.get(t_key, 1.0))
        tier_weighted_sum += (float(s["proficiency"]) * tw)
        tier_weight_sum += tw

    pillar_proficiency = (tier_weighted_sum / tier_weight_sum) if tier_weight_sum > 0 else None
    pillar_status = PILLAR_ASSESSED if coverage_ratio >= 0.5 else PILLAR_PARTIALLY_ASSESSED

    return {
        "name": pillar_name,
        "proficiency": round(pillar_proficiency, 1) if pillar_proficiency is not None else None,
        "raw_proficiency": pillar_proficiency,
        "assessed_count": assessed_count,
        "total_count": total_count,
        "coverage_display": f"{assessed_count}/{total_count}",
        "coverage_ratio": round(coverage_ratio, 4),
        "status": pillar_status
    }


# -----------------------------------------------------------------------------
# 5.6 READINESS (Two explicit numbers, always both shown, never mixed)
# -----------------------------------------------------------------------------

def calculate_readiness(skills: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes canonical readiness numbers:
    W(skill) = tierWeight(skill) (1.5 / 1.0 / 0.7)
    VerifiedScore = Σ(P_skill × W) / Σ(W)  (over ASSESSED skills only)
    WeightedCoverage = Σ(W of assessed skills) / Σ(W of all required skills)
    MandatoryCoverage = assessed mandatory / total mandatory
    ProjectedReadiness = VerifiedScore × (0.4 + 0.6 × WeightedCoverage)
    
    Provisional badge shown if MandatoryCoverage < 1 OR WeightedCoverage < 0.6.
    """
    if not skills:
        return {
            "verified_score": None,
            "projected_readiness": None,
            "weighted_coverage": 0.0,
            "mandatory_coverage": 0.0,
            "is_provisional": True,
            "missing_mandatory_skills": [],
            "skills_mastered_count": 0,
            "skills_demonstrated_count": 0,
            "assessed_skills_count": 0,
            "total_skills_count": 0,
            "formula_breakdown": "No evidence yet",
            "readiness_label": "No evidence yet"
        }

    total_weight_all = 0.0
    assessed_weight_sum = 0.0
    assessed_weighted_score = 0.0

    mandatory_total = 0
    mandatory_assessed = 0
    missing_mandatory_names = []

    assessed_count = 0
    mastered_count = 0

    for s in skills:
        t_key = str(s.get("tier", "PREFERRED")).upper().strip()
        w = float(TIER_WEIGHTS.get(t_key, 1.0))
        total_weight_all += w

        is_mandatory = (t_key == "MANDATORY")
        if is_mandatory:
            mandatory_total += 1

        prof = s.get("proficiency")
        stat = s.get("status")

        if prof is not None:
            assessed_count += 1
            assessed_weight_sum += w
            assessed_weighted_score += (float(prof) * w)
            if is_mandatory:
                mandatory_assessed += 1
            if stat == STATUS_VERIFIED_STRONG:
                mastered_count += 1
        else:
            if is_mandatory:
                missing_mandatory_names.append(s.get("name") or s.get("skill_id") or "Mandatory Skill")

    weighted_coverage = (assessed_weight_sum / total_weight_all) if total_weight_all > 0 else 0.0
    mandatory_coverage = (mandatory_assessed / mandatory_total) if mandatory_total > 0 else 1.0

    if assessed_weight_sum > 0:
        verified_score = assessed_weighted_score / assessed_weight_sum
        projected_readiness = verified_score * (0.4 + 0.6 * weighted_coverage)
    else:
        verified_score = None
        projected_readiness = None

    is_provisional = (mandatory_coverage < 1.0) or (weighted_coverage < 0.6)

    # Formula breakdown tooltip text
    if verified_score is not None and projected_readiness is not None:
        vs_disp = round(verified_score, 1)
        cov_disp = round(weighted_coverage, 2)
        pr_disp = round(projected_readiness, 1)
        formula_str = (
            f"Projected Readiness = Verified Score ({vs_disp}) × "
            f"(0.4 + 0.6 × Weighted Coverage ({cov_disp})) = {pr_disp}"
        )
    else:
        formula_str = "No evidence yet"

    return {
        "verified_score": round(verified_score, 1) if verified_score is not None else None,
        "raw_verified_score": verified_score,
        "projected_readiness": round(projected_readiness, 1) if projected_readiness is not None else None,
        "raw_projected_readiness": projected_readiness,
        "weighted_coverage": round(weighted_coverage, 4),
        "mandatory_coverage": round(mandatory_coverage, 4),
        "is_provisional": is_provisional,
        "missing_mandatory_skills": missing_mandatory_names,
        "skills_mastered_count": mastered_count,
        "skills_demonstrated_count": assessed_count,
        "assessed_skills_count": assessed_count,
        "total_skills_count": len(skills),
        "formula_breakdown": formula_str,
        "readiness_label": "PROVISIONAL" if is_provisional else "ESTABLISHED"
    }


# -----------------------------------------------------------------------------
# 5.7 TREND
# -----------------------------------------------------------------------------

def calculate_trend(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes readiness trend:
    - Compute ONLY when there are ≥ 3 assessment sessions on different days.
    - Otherwise returns "Not enough data yet" (no Declining label with one data point).
    - Slope = linear regression of session-level ProjectedReadiness over time (points per week).
    - Label: IMPROVING (> +2/week), FLAT (±2), DECLINING (< -2).
    - Baseline vs latest compares first session's VerifiedScore to latest session's VerifiedScore.
    """
    if not sessions:
        return {
            "has_enough_data": False,
            "trend_label": TREND_NOT_ENOUGH_DATA,
            "slope_per_week": None,
            "confidence_label": "None",
            "distinct_days_count": 0,
            "baseline_vs_latest": None
        }

    # Group by calendar date (in ISO date string YYYY-MM-DD)
    date_sessions: Dict[str, Dict[str, Any]] = {}

    for s in sessions:
        raw_dt = s.get("created_at") or s.get("date") or s.get("timestamp")
        pr = s.get("projected_readiness")
        vs = s.get("verified_score")

        if pr is None and vs is None:
            continue

        d_str = None
        epoch_sec = 0.0
        if isinstance(raw_dt, datetime):
            d_str = raw_dt.strftime("%Y-%m-%d")
            epoch_sec = raw_dt.timestamp()
        elif isinstance(raw_dt, date):
            d_str = raw_dt.strftime("%Y-%m-%d")
            epoch_sec = datetime(raw_dt.year, raw_dt.month, raw_dt.day, tzinfo=timezone.utc).timestamp()
        elif isinstance(raw_dt, str):
            try:
                parsed_dt = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
                d_str = parsed_dt.strftime("%Y-%m-%d")
                epoch_sec = parsed_dt.timestamp()
            except Exception:
                d_str = raw_dt[:10]
                epoch_sec = 0.0

        if not d_str:
            continue

        # Keep latest session for that day
        date_sessions[d_str] = {
            "date": d_str,
            "epoch_sec": epoch_sec,
            "projected_readiness": float(pr if pr is not None else (vs or 0.0)),
            "verified_score": float(vs if vs is not None else (pr or 0.0))
        }

    distinct_days = sorted(date_sessions.values(), key=lambda x: (x["epoch_sec"], x["date"]))
    distinct_count = len(distinct_days)

    if distinct_count < 3:
        return {
            "has_enough_data": False,
            "trend_label": TREND_NOT_ENOUGH_DATA,
            "slope_per_week": None,
            "confidence_label": "Low (insufficient history)",
            "distinct_days_count": distinct_count,
            "baseline_vs_latest": None
        }

    # Ordinary Least Squares (OLS) Linear Regression: x = days from first day, y = projected_readiness
    first_epoch = distinct_days[0]["epoch_sec"]
    xs = [((d["epoch_sec"] - first_epoch) / 86400.0) for d in distinct_days]
    ys = [d["projected_readiness"] for d in distinct_days]

    n = float(len(xs))
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = sum((x - mean_x) ** 2 for x in xs)

    if denominator > 0:
        slope_per_day = numerator / denominator
    else:
        slope_per_day = 0.0

    slope_per_week = slope_per_day * 7.0

    if slope_per_week > 2.0:
        label = TREND_IMPROVING
    elif slope_per_week < -2.0:
        label = TREND_DECLINING
    else:
        label = TREND_FLAT

    if distinct_count >= 8:
        conf_lbl = "High"
    elif distinct_count >= 5:
        conf_lbl = "Moderate"
    else:
        conf_lbl = "Low"

    first_vs = distinct_days[0]["verified_score"]
    latest_vs = distinct_days[-1]["verified_score"]
    delta = round(latest_vs - first_vs, 1)

    return {
        "has_enough_data": True,
        "trend_label": label,
        "slope_per_week": round(slope_per_week, 2),
        "confidence_label": conf_lbl,
        "distinct_days_count": distinct_count,
        "baseline_vs_latest": {
            "baseline_score": round(first_vs, 1),
            "latest_score": round(latest_vs, 1),
            "delta": delta,
            "improved": delta > 0
        }
    }


# -----------------------------------------------------------------------------
# 6. GAP ANALYSIS
# -----------------------------------------------------------------------------

def analyze_skill_gaps(skills: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Performs deterministic gap analysis complying with Section 6:
    - "Verified Skill Gaps" lists ONLY VERIFIED_GAP skills, sorted by:
      priority = W × (100 − P_skill) × interviewImportance
    - Specific, actionable remediation text.
    - "Not yet assessed" lists NOT_ASSESSED skills with "Take quick assessment", never in red.
    - "Low Evidence" lists LOW_EVIDENCE skills (provisional, never gaps).
    """
    verified_gaps = []
    not_assessed = []
    low_evidence = []
    developing = []
    verified_strong = []

    for s in skills:
        stat = s.get("status")
        p = s.get("proficiency")
        name = s.get("name") or s.get("skill_id") or "Technical Skill"
        t_key = str(s.get("tier", "PREFERRED")).upper().strip()
        w = float(TIER_WEIGHTS.get(t_key, 1.0))
        importance = float(s.get("importance", s.get("interview_importance", 3.0)) or 3.0)

        if stat == STATUS_NOT_ASSESSED or p is None:
            not_assessed.append({
                "skill_id": s.get("skill_id"),
                "name": name,
                "tier": t_key,
                "pillar": s.get("pillar", "Core Technical"),
                "status": STATUS_NOT_ASSESSED,
                "action_prompt": "Take quick assessment",
                "is_weakness": False
            })
        elif stat == STATUS_LOW_EVIDENCE:
            low_evidence.append({
                "skill_id": s.get("skill_id"),
                "name": name,
                "tier": t_key,
                "pillar": s.get("pillar", "Core Technical"),
                "proficiency": round(p, 1),
                "confidence": round(float(s.get("confidence", 0.2)), 2),
                "status": STATUS_LOW_EVIDENCE,
                "is_weakness": False,
                "note": "Provisional score pending additional evidence"
            })
        elif stat == STATUS_VERIFIED_GAP:
            gap_depth = max(0.0, 100.0 - float(p))
            priority = w * gap_depth * importance

            # Concrete, non-repeated remediation instruction
            failed_rubrics = s.get("failed_rubrics") or s.get("failed_rubric_items") or []
            if failed_rubrics:
                failed_summary = "; ".join(str(r) for r in failed_rubrics[:2])
                remediation = f"Targeted practice on: {failed_summary}. Complete practice assignment and re-test with Ava."
            else:
                remediation = f"Review foundational concepts in {name}, complete 3 practice problems, then submit a targeted verification block."

            verified_gaps.append({
                "skill_id": s.get("skill_id"),
                "name": name,
                "tier": t_key,
                "pillar": s.get("pillar", "Core Technical"),
                "proficiency": round(p, 1),
                "confidence": round(float(s.get("confidence", 0.5)), 2),
                "importance": importance,
                "priority": round(priority, 2),
                "status": STATUS_VERIFIED_GAP,
                "failed_rubric_items": failed_rubrics,
                "remediation_action": remediation,
                "is_weakness": True
            })
        elif stat == STATUS_DEVELOPING:
            developing.append({
                "skill_id": s.get("skill_id"),
                "name": name,
                "tier": t_key,
                "proficiency": round(p, 1),
                "status": STATUS_DEVELOPING
            })
        elif stat == STATUS_VERIFIED_STRONG:
            verified_strong.append({
                "skill_id": s.get("skill_id"),
                "name": name,
                "tier": t_key,
                "proficiency": round(p, 1),
                "status": STATUS_VERIFIED_STRONG
            })

    # Sort gaps descending by computed priority
    verified_gaps.sort(key=lambda x: x["priority"], reverse=True)

    return {
        "verified_skill_gaps": verified_gaps,
        "not_yet_assessed": not_assessed,
        "low_evidence_skills": low_evidence,
        "developing_skills": developing,
        "verified_strong_skills": verified_strong,
        "summary": {
            "gap_count": len(verified_gaps),
            "unassessed_count": len(not_assessed),
            "low_evidence_count": len(low_evidence),
            "strong_count": len(verified_strong)
        }
    }


# -----------------------------------------------------------------------------
# COMPLETE UNIFIED READINESS BUILDER
# -----------------------------------------------------------------------------

def build_unified_readiness_object(
    skills_data: List[Dict[str, Any]],
    sessions_history: Optional[List[Dict[str, Any]]] = None,
    target_role: str = "AI/ML Engineer"
) -> Dict[str, Any]:
    """
    Constructs the canonical readiness object returned by GET /api/readiness.
    Every page reads this identical payload.
    """
    processed_skills = []
    pillars_map: Dict[str, List[Dict[str, Any]]] = {}

    for s in skills_data:
        ev_items = s.get("evidence") or []
        p_skill, sum_w = calculate_skill_proficiency(ev_items)

        # Subskills count
        sub_tested = s.get("subskills_tested") or set()
        sub_total = s.get("total_subskills_count", 3)
        c_skill = calculate_skill_confidence(sum_w, sub_tested, sub_total)

        status = classify_skill_status(p_skill, c_skill)

        skill_obj = {
            "skill_id": s.get("skill_id"),
            "name": s.get("name") or s.get("skill_id"),
            "tier": str(s.get("tier", "PREFERRED")).upper(),
            "pillar": s.get("pillar", "Core Engineering"),
            "importance": float(s.get("importance", 3.0)),
            "proficiency": p_skill,
            "confidence": c_skill,
            "status": status,
            "evidence_count": len(ev_items),
            "failed_rubrics": s.get("failed_rubrics", [])
        }
        processed_skills.append(skill_obj)

        p_name = skill_obj["pillar"]
        if p_name not in pillars_map:
            pillars_map[p_name] = []
        pillars_map[p_name].append(skill_obj)

    # 1. Readiness
    readiness = calculate_readiness(processed_skills)

    # 2. Pillars
    pillars = [aggregate_pillar(p_skills, p_name) for p_name, p_skills in pillars_map.items()]

    # 3. Gap Analysis
    gap_analysis = analyze_skill_gaps(processed_skills)

    # 4. Trend
    trend = calculate_trend(sessions_history or [])

    return {
        "target_role": target_role,
        "readiness": readiness,
        "pillars": pillars,
        "gap_analysis": gap_analysis,
        "skills_map": processed_skills,
        "trend": trend
    }


# -----------------------------------------------------------------------------
# CANONICAL ROLE PROFILE & DATABASE EVALUATION ADAPTER
# -----------------------------------------------------------------------------

def get_canonical_role_skills(target_role: str = "AI/ML Engineer") -> List[Dict[str, Any]]:
    """
    Returns the canonical template skills for a target role matching Section 3.4.
    Used when a candidate has not yet saved a customized role profile.
    """
    r = (target_role or "").lower()
    if "ai" in r or "ml" in r or "machine learning" in r or "deep learning" in r:
        return [
            # Pillar 1: Programming & Data
            {
                "skill_id": "python_ml",
                "name": "Python for ML (NumPy/Pandas)",
                "pillar": "Programming & Data",
                "tier": "MANDATORY",
                "importance": 5.0,
                "subskills": ["vectorisation", "broadcasting", "memory_management"],
                "total_subskills_count": 3
            },
            {
                "skill_id": "sql_opt",
                "name": "SQL & Query Optimization",
                "pillar": "Programming & Data",
                "tier": "PREFERRED",
                "importance": 4.0,
                "subskills": ["indexing", "window_functions", "join_strategies"],
                "total_subskills_count": 3
            },
            {
                "skill_id": "data_cleaning",
                "name": "Data Cleaning & Preprocessing",
                "pillar": "Programming & Data",
                "tier": "SUPPORTING",
                "importance": 3.0,
                "subskills": ["imputation", "outlier_detection", "feature_scaling"],
                "total_subskills_count": 3
            },
            # Pillar 2: ML Fundamentals
            {
                "skill_id": "supervised_learning",
                "name": "Supervised Learning & Regularization",
                "pillar": "ML Fundamentals",
                "tier": "MANDATORY",
                "importance": 5.0,
                "subskills": ["bias_variance", "l1_l2_regularization", "tree_ensembles"],
                "total_subskills_count": 3
            },
            {
                "skill_id": "model_eval",
                "name": "Model Evaluation & Imbalanced Metrics",
                "pillar": "ML Fundamentals",
                "tier": "MANDATORY",
                "importance": 5.0,
                "subskills": ["precision_recall", "roc_auc", "f1_score"],
                "total_subskills_count": 3
            },
            {
                "skill_id": "linear_algebra",
                "name": "Linear Algebra for ML",
                "pillar": "ML Fundamentals",
                "tier": "SUPPORTING",
                "importance": 3.0,
                "subskills": ["matrix_factorization", "eigenvalues_pca", "gradient_descent"],
                "total_subskills_count": 3
            },
            {
                "skill_id": "prob_stats",
                "name": "Probability & Statistics",
                "pillar": "ML Fundamentals",
                "tier": "SUPPORTING",
                "importance": 3.0,
                "subskills": ["bayes_theorem", "distributions", "hypothesis_testing"],
                "total_subskills_count": 3
            },
            # Pillar 3: Deep Learning
            {
                "skill_id": "neural_networks",
                "name": "Neural Networks & Backpropagation",
                "pillar": "Deep Learning",
                "tier": "PREFERRED",
                "importance": 4.0,
                "subskills": ["activation_functions", "loss_functions", "optimization_algorithms"],
                "total_subskills_count": 3
            },
            {
                "skill_id": "transformers",
                "name": "Transformer Architecture & Self-Attention",
                "pillar": "Deep Learning",
                "tier": "MANDATORY",
                "importance": 5.0,
                "subskills": ["multi_head_attention", "positional_encoding", "layer_norm"],
                "total_subskills_count": 3
            },
            {
                "skill_id": "nlp_processing",
                "name": "NLP & Text Processing",
                "pillar": "Deep Learning",
                "tier": "SUPPORTING",
                "importance": 3.0,
                "subskills": ["tokenization", "embeddings", "sequence_modeling"],
                "total_subskills_count": 3
            },
            # Pillar 4: GenAI
            {
                "skill_id": "llm_fundamentals",
                "name": "LLM Fundamentals",
                "pillar": "GenAI",
                "tier": "PREFERRED",
                "importance": 4.0,
                "subskills": ["prompt_engineering", "kv_caching", "fine_tuning_lora"],
                "total_subskills_count": 3
            },
            {
                "skill_id": "rag_mitigation",
                "name": "RAG & Hallucination Mitigation",
                "pillar": "GenAI",
                "tier": "PREFERRED",
                "importance": 4.0,
                "subskills": ["vector_search", "chunking_strategies", "groundedness_eval"],
                "total_subskills_count": 3
            },
            # Pillar 5: Production ML
            {
                "skill_id": "model_deployment",
                "name": "Model Deployment & Productionization",
                "pillar": "Production ML",
                "tier": "PREFERRED",
                "importance": 4.0,
                "subskills": ["onnx_quantization", "api_serving", "batch_vs_realtime"],
                "total_subskills_count": 3
            },
            {
                "skill_id": "ml_system_design",
                "name": "ML System Design & Feature Stores",
                "pillar": "Production ML",
                "tier": "MANDATORY",
                "importance": 5.0,
                "subskills": ["feature_stores", "streaming_pipelines", "latency_sla"],
                "total_subskills_count": 3
            },
            {
                "skill_id": "monitoring_drift",
                "name": "Monitoring & Data Drift",
                "pillar": "Production ML",
                "tier": "SUPPORTING",
                "importance": 3.0,
                "subskills": ["concept_drift", "data_drift", "model_observability"],
                "total_subskills_count": 3
            },
            # Pillar 6: Interview Execution
            {
                "skill_id": "problem_scoping",
                "name": "Problem Clarification & Scoping",
                "pillar": "Interview Execution",
                "tier": "PREFERRED",
                "importance": 4.0,
                "subskills": ["requirements_gathering", "metric_selection", "tradeoff_articulation"],
                "total_subskills_count": 3
            },
            {
                "skill_id": "star_stories",
                "name": "Behavioral/STAR stories",
                "pillar": "Interview Execution",
                "tier": "SUPPORTING",
                "importance": 3.0,
                "subskills": ["conflict_resolution", "project_ownership", "technical_leadership"],
                "total_subskills_count": 3
            },
            {
                "skill_id": "dsa_fundamentals",
                "name": "Coding Fundamentals (DSA)",
                "pillar": "Interview Execution",
                "tier": "PREFERRED",
                "importance": 4.0,
                "subskills": ["arrays_hashing", "two_pointers", "graphs_trees"],
                "total_subskills_count": 3
            }
        ]

    # Default general SDE role profile
    return [
        {
            "skill_id": "dsa_arrays_strings",
            "name": "Arrays & Strings",
            "pillar": "Data Structures & Algorithms",
            "tier": "MANDATORY",
            "importance": 5.0,
            "subskills": ["sliding_window", "two_pointers", "prefix_sums"],
            "total_subskills_count": 3
        },
        {
            "skill_id": "dsa_trees_graphs",
            "name": "Trees & Graphs",
            "pillar": "Data Structures & Algorithms",
            "tier": "MANDATORY",
            "importance": 5.0,
            "subskills": ["dfs_bfs", "shortest_path", "topological_sort"],
            "total_subskills_count": 3
        },
        {
            "skill_id": "sys_caching",
            "name": "Caching & Memory Hierarchy",
            "pillar": "System Design",
            "tier": "MANDATORY",
            "importance": 4.0,
            "subskills": ["redis", "eviction_policies", "cache_invalidation"],
            "total_subskills_count": 3
        },
        {
            "skill_id": "cs_concurrency",
            "name": "Concurrency & Operating Systems",
            "pillar": "Core CS",
            "tier": "MANDATORY",
            "importance": 4.0,
            "subskills": ["threads_locks", "deadlocks", "async_event_loops"],
            "total_subskills_count": 3
        },
        {
            "skill_id": "cs_dbms",
            "name": "DBMS Internals & Indexing",
            "pillar": "Core CS",
            "tier": "PREFERRED",
            "importance": 4.0,
            "subskills": ["b_trees", "acid_isolation", "query_plans"],
            "total_subskills_count": 3
        },
        {
            "skill_id": "sys_scalability",
            "name": "Distributed Scalability",
            "pillar": "System Design",
            "tier": "PREFERRED",
            "importance": 4.0,
            "subskills": ["sharding", "load_balancing", "consensus"],
            "total_subskills_count": 3
        },
        {
            "skill_id": "soft_tradeoffs",
            "name": "Technical Trade-off Articulation",
            "pillar": "Interview Execution",
            "tier": "SUPPORTING",
            "importance": 3.0,
            "subskills": ["communication", "star_method", "architecture_defense"],
            "total_subskills_count": 3
        }
    ]


def evaluate_candidate_readiness(
    user_id: str,
    target_role: str = "AI/ML Engineer",
    supabase_client=None
) -> Dict[str, Any]:
    """
    Evaluates candidate readiness against target role requirements:
    - Gathers candidate evidence records from Supabase / fallback registry
    - Calibrates P_skill and C_skill for each required skill
    - Computes VerifiedScore, WeightedCoverage, and ProjectedReadiness
    - Builds identical unified readiness object for Dashboard, Roadmap, and Analytics
    """
    clean_uid = str(user_id or "user_default").strip()

    # 1. Fetch skills definition for role
    template_skills = get_canonical_role_skills(target_role)

    # 2. Gather candidate evidence from EvidenceRegistryService if available
    evidence_by_skill: Dict[str, List[Dict[str, Any]]] = {}
    subskills_tested_by_skill: Dict[str, Set[str]] = {}
    sessions_history: List[Dict[str, Any]] = []

    try:
        from services.evidence_registry_service import EvidenceRegistryService
        raw_evidence = EvidenceRegistryService.get_evidence_for_candidate(
            user_id=clean_uid,
            supabase_client=supabase_client
        )
        now_dt = datetime.now(timezone.utc)

        for ev in (raw_evidence or []):
            sk_id = ev.get("skill_id")
            if not sk_id:
                continue

            # Parse score and age
            score_val = ev.get("normalized_score") if ev.get("normalized_score") is not None else ev.get("raw_score")
            if score_val is None:
                continue

            created_raw = ev.get("created_at")
            age_days = 0.0
            if created_raw:
                try:
                    ev_dt = datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))
                    age_days = max(0.0, (now_dt - ev_dt).total_seconds() / 86400.0)
                except Exception:
                    age_days = 0.0

            diff = ev.get("difficulty", "MEDIUM")
            stype = ev.get("source_type", "SHORT_ANSWER")

            # Map source_type to standard evidence types
            mapped_type = "SHORT_ANSWER"
            if "code" in str(stype).lower() or "submission" in str(stype).lower():
                mapped_type = "CODE"
            elif "interview" in str(stype).lower():
                mapped_type = "MOCK_INTERVIEW"
            elif "assignment" in str(stype).lower():
                mapped_type = "PRACTICE_ASSIGNMENT"
            elif "mcq" in str(stype).lower():
                mapped_type = "MCQ"

            item = {
                "score": float(score_val),
                "age_in_days": age_days,
                "difficulty": diff,
                "evidence_type": mapped_type,
                "is_attempted": True
            }

            if sk_id not in evidence_by_skill:
                evidence_by_skill[sk_id] = []
            evidence_by_skill[sk_id].append(item)

            # Subskills
            meta = ev.get("metadata")
            if isinstance(meta, str):
                try:
                    import json
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            if isinstance(meta, dict) and meta.get("subskill"):
                if sk_id not in subskills_tested_by_skill:
                    subskills_tested_by_skill[sk_id] = set()
                subskills_tested_by_skill[sk_id].add(str(meta["subskill"]))

    except Exception as ex:
        logger.warning(f"Could not load external evidence for {clean_uid}: {ex}")

    # 3. Assemble skills data with evidence
    skills_data = []
    for t_skill in template_skills:
        sk_id = t_skill["skill_id"]
        ev_list = evidence_by_skill.get(sk_id, [])
        sub_tested = subskills_tested_by_skill.get(sk_id, set())

        skills_data.append({
            "skill_id": sk_id,
            "name": t_skill["name"],
            "pillar": t_skill["pillar"],
            "tier": t_skill["tier"],
            "importance": t_skill["importance"],
            "total_subskills_count": t_skill.get("total_subskills_count", 3),
            "evidence": ev_list,
            "subskills_tested": sub_tested
        })

    # 4. Build and return canonical object
    return build_unified_readiness_object(
        skills_data=skills_data,
        sessions_history=sessions_history,
        target_role=target_role
    )

