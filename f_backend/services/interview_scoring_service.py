"""
Phase 4: Deterministic Scoring, Grade & Verdict Engine (Pure Functions, Fully Unit-Tested)
Formula Version: v1
Operating Rules R1, R2, R3, R9:
  - Per-turn score = weighted mean of rubric criterion scores (0-1); non-'ok' turns have no score.
  - Dimension score = weighted mean across contributing OK turns (NULL if 0 evidence, LOW_CONFIDENCE if < 2 turns).
  - Delivery dimensions return NULL ('Not evaluated') if speech metrics are NULL.
  - Overall score = weighted mean over EVALUATED dimensions only (weights renormalized, never zero-filled).
  - Confidence is computed separately and never merged into overall score.
  - Report statuses: EVALUATED, PARTIAL, INCOMPLETE_INSUFFICIENT_DATA, EVALUATION_FAILED.
  - Missing data NEVER yields a score, grade F, or Strong Reject.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from services.interview_scoring_config import (
    DIMENSION_CONFIG,
    FORMULA_VERSION,
    GRADE_BANDS,
    MIN_COVERAGE_FOR_ESTABLISHED,
    MIN_COVERAGE_FOR_PARTIAL,
    MIN_SUBSTANTIVE_TURNS_FOR_EVALUATED,
    MIN_SUBSTANTIVE_TURNS_FOR_STRONG_REJECT,
    MIN_TURNS_PER_DIMENSION,
    MIN_WORDS_FOR_PARTIAL,
    REPORT_STATUS_EVALUATED,
    REPORT_STATUS_FAILED,
    REPORT_STATUS_INCOMPLETE,
    REPORT_STATUS_PARTIAL,
    WPM_OPTIMAL_MAX,
    WPM_OPTIMAL_MIN,
)


def _safe_json(val: Any, default: Any) -> Any:
    if val is None:
        return default
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return default
    return default


def compute_per_turn_score(evaluation: Dict[str, Any]) -> Optional[float]:
    """
    Per-turn score = weighted mean of rubric criterion scores (0.0 - 1.0).
    Turns with status other than 'ok' have no score (None).
    """
    if not isinstance(evaluation, dict) or evaluation.get("status") != "ok":
        return None

    rubric = _safe_json(evaluation.get("rubric_scores_json"), {})
    criteria = rubric.get("criteria") if isinstance(rubric, dict) else None
    if isinstance(criteria, list) and len(criteria) > 0:
        w_sum = 0.0
        weighted = 0.0
        for c in criteria:
            try:
                w = float(c.get("weight", 1.0))
                s = float(c.get("score"))
            except (TypeError, ValueError):
                continue
            if w > 0:
                s_clamped = max(0.0, min(1.0, s))
                w_sum += w
                weighted += w * s_clamped
        if w_sum > 0:
            return round(weighted / w_sum, 4)

    norm = evaluation.get("normalized_score")
    if norm is not None:
        try:
            return round(max(0.0, min(1.0, float(norm))), 4)
        except (TypeError, ValueError):
            return None
    return None


def compute_speech_delivery_score(speech_metrics_list: List[Dict[str, Any]]) -> Optional[float]:
    """
    Deterministic delivery score (0.0 - 1.0) from measured speech telemetry.
    Returns None if timing is missing across all turns.
    """
    measurable = sorted(
        [m for m in (speech_metrics_list or []) if isinstance(m, dict) and m.get("wpm") is not None],
        key=lambda x: str(x.get("turn_id") or ""),
    )
    if not measurable:
        return None

    scores: List[float] = []
    for m in measurable:
        wpm = float(m["wpm"])
        if WPM_OPTIMAL_MIN <= wpm <= WPM_OPTIMAL_MAX:
            pace_s = 1.0
        elif wpm < WPM_OPTIMAL_MIN:
            pace_s = max(0.3, 1.0 - (WPM_OPTIMAL_MIN - wpm) / 100.0)
        else:
            pace_s = max(0.3, 1.0 - (wpm - WPM_OPTIMAL_MAX) / 100.0)

        wc = max(1, int(m.get("word_count") or 1))
        fillers = int(m.get("filler_count") or 0)
        fluency_s = max(0.2, 1.0 - (fillers / float(wc)) * 3.0)
        scores.append(0.6 * pace_s + 0.4 * fluency_s)

    return round(sum(scores) / len(scores), 4)


def compute_dimension_scores(
    evaluations: List[Dict[str, Any]],
    speech_metrics_list: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Deterministically computes dimension scores in [0.0, 1.0] (and 0-100 display scale).
    Sorts all inputs by turn_id/id so turn ordering never alters output.
    """
    ok_evals = sorted(
        [
            e for e in (evaluations or [])
            if isinstance(e, dict) and e.get("status") == "ok" and compute_per_turn_score(e) is not None
        ],
        key=lambda e: (str(e.get("turn_id") or ""), str(e.get("id") or "")),
    )
    speech_delivery = compute_speech_delivery_score(speech_metrics_list or [])

    dimensions_out: List[Dict[str, Any]] = []
    for dim_name, cfg in DIMENSION_CONFIG.items():
        target_criteria = set(cfg["criteria"])
        is_delivery = bool(cfg.get("is_delivery", False))
        is_critical = bool(cfg.get("critical", False))

        weighted_sum = 0.0
        weight_sum = 0.0
        contributing_turns: List[str] = []
        evidence_quotes: List[Dict[str, Any]] = []

        for ev in ok_evals:
            rubric = _safe_json(ev.get("rubric_scores_json"), {})
            criteria = rubric.get("criteria") if isinstance(rubric, dict) else []
            matched = False
            for crit in (criteria or []):
                cname = str(crit.get("criterion") or "").strip().lower()
                if cname in target_criteria:
                    try:
                        cw = float(crit.get("weight", 0.2))
                        cs = max(0.0, min(1.0, float(crit.get("score"))))
                    except (TypeError, ValueError):
                        continue
                    if cw > 0:
                        weighted_sum += cw * cs
                        weight_sum += cw
                        matched = True
                        q = (crit.get("quoted_justification") or "").strip()
                        if q:
                            evidence_quotes.append({
                                "turn_id": ev.get("turn_id"),
                                "criterion": cname,
                                "score": round(cs, 4),
                                "quote": q,
                            })
            if matched and ev.get("turn_id"):
                contributing_turns.append(str(ev["turn_id"]))

        unique_turns = sorted(set(contributing_turns))

        if is_delivery and speech_delivery is None:
            dimensions_out.append({
                "name": dim_name,
                "weight": cfg["weight"],
                "critical": is_critical,
                "is_delivery": True,
                "normalized_score": None,
                "score": None,
                "grade": None,
                "status": "Not evaluated",
                "reason": "speech_metrics_unavailable",
                "confidence_label": "NONE",
                "contributing_turns": [],
                "turn_count": 0,
                "evidence": [],
            })
            continue

        if weight_sum == 0.0:
            dimensions_out.append({
                "name": dim_name,
                "weight": cfg["weight"],
                "critical": is_critical,
                "is_delivery": is_delivery,
                "normalized_score": None,
                "score": None,
                "grade": None,
                "status": "Not evaluated",
                "reason": "no_contributing_evidence",
                "confidence_label": "NONE",
                "contributing_turns": [],
                "turn_count": 0,
                "evidence": [],
            })
            continue

        rubric_mean = weighted_sum / weight_sum
        if is_delivery and speech_delivery is not None:
            dim_norm = round(max(0.0, min(1.0, 0.5 * rubric_mean + 0.5 * speech_delivery)), 4)
        else:
            dim_norm = round(max(0.0, min(1.0, rubric_mean)), 4)

        turn_count = len(unique_turns)
        conf_label = "LOW_CONFIDENCE" if turn_count < MIN_TURNS_PER_DIMENSION else "ESTABLISHED"
        status_str = "LIMITED_EVIDENCE" if conf_label == "LOW_CONFIDENCE" else "EVALUATED"
        dim_grade = _grade_for_score(dim_norm)

        dimensions_out.append({
            "name": dim_name,
            "weight": cfg["weight"],
            "critical": is_critical,
            "is_delivery": is_delivery,
            "normalized_score": dim_norm,
            "score": round(dim_norm * 100.0, 1),
            "grade": dim_grade["grade"],
            "color": dim_grade["color"],
            "status": status_str,
            "confidence_label": conf_label,
            "contributing_turns": unique_turns,
            "turn_count": turn_count,
            "evidence": evidence_quotes[:6],
            "formula_inputs": {
                "formula_version": FORMULA_VERSION,
                "rubric_weighted_sum": round(weighted_sum, 4),
                "rubric_weight_sum": round(weight_sum, 4),
                "rubric_mean": round(rubric_mean, 4),
                "speech_delivery_score": speech_delivery if is_delivery else None,
                "target_criteria": sorted(target_criteria),
                "contributing_turn_count": turn_count,
            },
        })

    return dimensions_out


def _grade_for_score(norm_score: float) -> Dict[str, str]:
    for letter, floor, label, color in GRADE_BANDS:
        if norm_score >= floor:
            return {"grade": letter, "label": label, "color": color}
    return {"grade": "F", "label": "Below Bar", "color": "#ef4444"}


def compute_overall_score_and_coverage(
    dimension_rows: List[Dict[str, Any]],
) -> Tuple[Optional[float], Optional[float], float]:
    """
    Overall score = weighted mean over EVALUATED dimensions only (weights renormalized).
    Coverage = evaluated dimension weight / total dimension weight.
    Returns (overall_norm_0_to_1, overall_100, coverage_0_to_1).
    """
    total_weight = sum(float(d.get("weight") or 0.0) for d in dimension_rows)
    evaluated = [d for d in dimension_rows if d.get("normalized_score") is not None]
    eval_weight = sum(float(d.get("weight") or 0.0) for d in evaluated)

    coverage = round(eval_weight / total_weight, 4) if total_weight > 0 else 0.0
    if not evaluated or eval_weight <= 0.0:
        return None, None, coverage

    overall_norm = sum(float(d["weight"]) * float(d["normalized_score"]) for d in evaluated) / eval_weight
    overall_norm = round(max(0.0, min(1.0, overall_norm)), 4)
    return overall_norm, round(overall_norm * 100.0, 1), coverage


def compute_confidence(
    substantive_turns: int,
    coverage: float,
    evaluations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Confidence is separate from overall score: f(substantive_turns, coverage, evaluator agreement).
    """
    turn_factor = min(1.0, max(0, substantive_turns) / 5.0)
    cov_factor = min(1.0, max(0.0, coverage))

    max_delta = 0.0
    flagged = False
    for ev in (evaluations or []):
        rubric = _safe_json(ev.get("rubric_scores_json"), {})
        if isinstance(rubric, dict):
            delta = float(rubric.get("disagreement_delta") or 0.0)
            if delta > max_delta:
                max_delta = delta
            if rubric.get("disagreement_flagged"):
                flagged = True

    agreement_factor = max(0.2, 1.0 - (max_delta if flagged else 0.0) * 0.5)
    conf_score = round(max(0.0, min(1.0, 0.45 * turn_factor + 0.40 * cov_factor + 0.15 * agreement_factor)), 4)
    if conf_score >= 0.70:
        label = "HIGH"
    elif conf_score >= 0.40:
        label = "MEDIUM"
    else:
        label = "LOW"

    return {
        "score": conf_score,
        "label": label,
        "substantive_turns": substantive_turns,
        "coverage": coverage,
        "evaluator_disagreement_flagged": flagged,
    }


def determine_report_status(
    turns: List[Dict[str, Any]],
    evaluations: List[Dict[str, Any]],
    data_sufficiency: Dict[str, Any],
    coverage: float,
) -> Tuple[str, str, List[str]]:
    """
    Deterministic state machine for report_status:
      - EVALUATION_FAILED
      - INCOMPLETE_INSUFFICIENT_DATA
      - PARTIAL
      - EVALUATED
    Returns (report_status, explanation, missing_reasons).
    """
    cand_turns = [
        t for t in (turns or [])
        if t.get("speaker") == "candidate" and (t.get("turn_status") or "") != "small_talk"
    ]
    answered_turns = [t for t in cand_turns if (t.get("turn_status") or "") == "answered"]
    ok_evals = [e for e in (evaluations or []) if e.get("status") == "ok" and compute_per_turn_score(e) is not None]
    failed_evals = [e for e in (evaluations or []) if e.get("status") == "failed"]

    substantive_turns = int(data_sufficiency.get("answered_substantive_turns") or 0)
    total_words = int(data_sufficiency.get("total_words") or 0)

    # 1. Evaluation Failed (explicit failed evaluations OR candidate answered turns present but 0 evaluations succeeded)
    if (failed_evals and len(ok_evals) == 0) or (len(answered_turns) > 0 and len(ok_evals) == 0):
        return (
            REPORT_STATUS_FAILED,
            "We couldn't evaluate this interview due to an evaluation failure. Candidate responses are preserved; please retry evaluation.",
            ["evaluations_failed_or_pending"],
        )

    # 2. Incomplete / Insufficient Data
    missing_reasons: List[str] = []
    if len(cand_turns) == 0:
        missing_reasons.append("zero_candidate_turns")
    if substantive_turns < MIN_SUBSTANTIVE_TURNS_FOR_EVALUATED:
        missing_reasons.append(f"substantive_turns ({substantive_turns} < {MIN_SUBSTANTIVE_TURNS_FOR_EVALUATED})")
    if total_words < MIN_WORDS_FOR_PARTIAL:
        missing_reasons.append(f"total_words ({total_words} < {MIN_WORDS_FOR_PARTIAL})")
    if coverage < MIN_COVERAGE_FOR_PARTIAL and len(ok_evals) > 0:
        missing_reasons.append(f"dimension_coverage ({coverage:.2f} < {MIN_COVERAGE_FOR_PARTIAL:.2f})")

    if (
        len(cand_turns) == 0
        or substantive_turns < MIN_SUBSTANTIVE_TURNS_FOR_EVALUATED
        or total_words < MIN_WORDS_FOR_PARTIAL
        or coverage < MIN_COVERAGE_FOR_PARTIAL
    ):
        if len(cand_turns) == 0:
            msg = "No candidate responses were recorded in this session yet. Continue the interview to receive an evaluation."
        else:
            msg = f"Insufficient evaluated evidence ({substantive_turns} substantive turn(s), {total_words} words). Continue the interview for a full score."
        return REPORT_STATUS_INCOMPLETE, msg, missing_reasons

    # 3. Partial vs Evaluated
    if coverage < MIN_COVERAGE_FOR_ESTABLISHED or failed_evals:
        partial_reasons = []
        if coverage < MIN_COVERAGE_FOR_ESTABLISHED:
            partial_reasons.append(f"coverage ({coverage:.2f} < {MIN_COVERAGE_FOR_ESTABLISHED:.2f})")
        if failed_evals:
            partial_reasons.append(f"{len(failed_evals)} failed turn evaluation(s)")
        return (
            REPORT_STATUS_PARTIAL,
            f"Provisional evaluation based on partial evidence ({', '.join(partial_reasons)}).",
            partial_reasons,
        )

    return REPORT_STATUS_EVALUATED, "Interview fully evaluated from persisted candidate evidence.", []


def compute_grade(overall_norm: Optional[float], report_status: str) -> Optional[str]:
    """
    A grade is issued ONLY for EVALUATED ('A'..'F') and PARTIAL ('Provisional (X)').
    For INCOMPLETE or EVALUATION_FAILED, returns None.
    """
    if overall_norm is None:
        return None
    if report_status == REPORT_STATUS_EVALUATED:
        return _grade_for_score(overall_norm)["grade"]
    if report_status == REPORT_STATUS_PARTIAL:
        raw_g = _grade_for_score(overall_norm)["grade"]
        return f"Provisional ({raw_g})"
    return None


def compute_hiring_recommendation(
    report_status: str,
    overall_norm: Optional[float],
    dimension_rows: List[Dict[str, Any]],
    confidence: Dict[str, Any],
    substantive_turns: int,
) -> Optional[str]:
    """
    Only issued for EVALUATED or PARTIAL. Never produced from missing/failed/incomplete data.
    'Strong Reject' requires EVALUATED status AND >= min_turns_for_reject substantive answers AND high confidence.
    """
    if report_status not in (REPORT_STATUS_EVALUATED, REPORT_STATUS_PARTIAL) or overall_norm is None:
        return None

    if report_status == REPORT_STATUS_PARTIAL:
        if overall_norm >= 0.70:
            return "Provisional Leaning Hire (Needs More Evidence)"
        return "Needs More Evidence"

    crit_scores = [
        float(d["normalized_score"])
        for d in dimension_rows
        if d.get("critical") and d.get("normalized_score") is not None
    ]
    critical_min = min(crit_scores) if crit_scores else overall_norm
    conf_label = confidence.get("label", "LOW")

    if overall_norm >= 0.85 and critical_min >= 0.75 and conf_label in ("MEDIUM", "HIGH"):
        return "Strong Hire"
    if overall_norm >= 0.70 and critical_min >= 0.60:
        return "Hire"
    if overall_norm >= 0.55:
        return "Borderline / Needs Review"
    if (
        overall_norm < 0.40
        and substantive_turns >= MIN_SUBSTANTIVE_TURNS_FOR_STRONG_REJECT
        and conf_label == "HIGH"
    ):
        return "Strong Reject"
    return "Reject"


def score_interview_session(
    turns: List[Dict[str, Any]],
    evaluations: List[Dict[str, Any]],
    speech_metrics_list: List[Dict[str, Any]],
    data_sufficiency: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Master pure scoring pipeline combining persisted turns, evaluations, speech metrics,
    and data sufficiency under formula_version='v1'.
    """
    sorted_turns = sorted(
        list(turns or []),
        key=lambda t: (int(t.get("turn_index") if t.get("turn_index") is not None else 0), str(t.get("speaker") or ""), str(t.get("id") or "")),
    )
    sorted_evals = sorted(
        list(evaluations or []),
        key=lambda e: (str(e.get("turn_id") or ""), str(e.get("id") or "")),
    )

    dim_rows = compute_dimension_scores(sorted_evals, speech_metrics_list)
    overall_norm, overall_100, coverage = compute_overall_score_and_coverage(dim_rows)
    substantive_turns = int(data_sufficiency.get("answered_substantive_turns") or 0)
    confidence = compute_confidence(substantive_turns, coverage, sorted_evals)
    report_status, status_reason, missing_reasons = determine_report_status(
        sorted_turns, sorted_evals, data_sufficiency, coverage
    )

    # Gate scores/grade/recommendation strictly by report_status (Operating Rule R2)
    if report_status in (REPORT_STATUS_INCOMPLETE, REPORT_STATUS_FAILED):
        issued_score_norm = None
        issued_score_100 = None
        issued_grade = None
        issued_rec = None
    else:
        issued_score_norm = overall_norm
        issued_score_100 = overall_100
        issued_grade = compute_grade(overall_norm, report_status)
        issued_rec = compute_hiring_recommendation(
            report_status, overall_norm, dim_rows, confidence, substantive_turns
        )

    evaluated_dims = [d["name"] for d in dim_rows if d.get("normalized_score") is not None]
    unassessed_dims = [d["name"] for d in dim_rows if d.get("normalized_score") is None]

    return {
        "formula_version": FORMULA_VERSION,
        "report_status": report_status,
        "status_reason": status_reason,
        "missing_reasons": missing_reasons,
        "overall_score": issued_score_norm,
        "overall_score_100": issued_score_100,
        "grade": issued_grade,
        "recommendation": issued_rec,
        "coverage": coverage,
        "evaluated_dimensions_count": len(evaluated_dims),
        "total_dimensions_count": len(dim_rows),
        "unassessed_dimensions": unassessed_dims,
        "confidence": confidence,
        "dimensions": dim_rows,
        "data_sufficiency": data_sufficiency,
    }

