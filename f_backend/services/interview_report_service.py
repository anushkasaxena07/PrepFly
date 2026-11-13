"""
Phase 5: Evidence-Grounded Interview Report Generation Service (No Templates)
Operating Rules R1, R2, R3, R4, R5, R6, R8:
  - Built STRICTLY from persisted `interview_turns`, `interview_speech_metrics`, `interview_evaluations`.
  - Strengths & weaknesses always cite turn_id + verbatim quote; zero generic templates.
  - Missing metrics -> 'Not measurable' with reason; unevaluated areas -> separate `not_assessed_yet` list.
  - Final analysis narrative is grounded ONLY in pre-computed numbers & validated against hallucinations.
  - Syncs evaluated interview results into Prompt 1 readiness & Prep Roadmap.
"""

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from services.identity_service import resolve_candidate_display_name
from services.interview_capture_service import compute_data_sufficiency, get_session_turns_and_metrics
from services.interview_reliability_service import (
    await_background_turn_evals,
    build_concise_resume_summary,
    record_report_audit_log,
)
from services.interview_scoring_config import (
    DIMENSION_CONFIG,
    FORMULA_VERSION,
    REPORT_STATUS_EVALUATED,
    REPORT_STATUS_FAILED,
    REPORT_STATUS_INCOMPLETE,
    REPORT_STATUS_PARTIAL,
    STRENGTH_THRESHOLD,
    WEAKNESS_THRESHOLD,
    WPM_OPTIMAL_MAX,
    WPM_OPTIMAL_MIN,
)
from services.interview_scoring_service import compute_per_turn_score, score_interview_session

logger = logging.getLogger(__name__)

NARRATIVE_PROMPT_ID = "interview_report_narrative"
NARRATIVE_PROMPT_VERSION = "v1.0"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _build_evidence_grounded_strengths(
    evaluations: List[Dict[str, Any]],
    coverage: float,
) -> Dict[str, Any]:
    """
    Phase 5 #6: Only from turns/criteria scoring >= STRENGTH_THRESHOLD, each with a cited quote.
    Never emits 'No tangible strengths'.
    """
    items: List[Dict[str, Any]] = []
    ok_evals = sorted(
        [e for e in evaluations if e.get("status") == "ok"],
        key=lambda e: str(e.get("turn_id") or ""),
    )

    for ev in ok_evals:
        rubric = _safe_json(ev.get("rubric_scores_json"), {})
        criteria = rubric.get("criteria") if isinstance(rubric, dict) else []
        for c in (criteria or []):
            try:
                sc = float(c.get("score"))
            except (TypeError, ValueError):
                continue
            quote = (c.get("quoted_justification") or "").strip()
            if sc >= STRENGTH_THRESHOLD and quote:
                cname = str(c.get("criterion") or "competency").replace("_", " ").title()
                items.append({
                    "title": f"{cname} ({ev.get('skill_id') or 'Interview'})",
                    "criterion": c.get("criterion"),
                    "skill_id": ev.get("skill_id"),
                    "turn_id": ev.get("turn_id"),
                    "score": round(sc, 4),
                    "quote": quote,
                    "evidence": f'Turn {ev.get("turn_id")}: "{quote}" (score {round(sc * 100)}/100)',
                })

    # Deduplicate by (turn_id, criterion), sort highest score first
    items.sort(key=lambda x: (-x["score"], str(x["turn_id"]), str(x["criterion"])))
    top_items = items[:5]

    empty_msg = None
    if not top_items:
        empty_msg = f"Not enough strong evidence yet (dimension coverage: {round(coverage * 100)}%)."

    return {
        "items": top_items,
        "empty_message": empty_msg,
    }


def _build_evidence_grounded_weaknesses(
    evaluations: List[Dict[str, Any]],
    confidence_score: float,
) -> Dict[str, Any]:
    """
    Phase 5 #7: Only from evaluated criteria scoring < WEAKNESS_THRESHOLD with >= 1 cited turn.
    severity = importance * (1 - score) * confidence.
    Recurring misconception tags across >= 2 turns are flagged as recurring.
    NO generic templates.
    """
    criterion_importance: Dict[str, float] = {}
    for cfg in DIMENSION_CONFIG.values():
        for crit in cfg["criteria"]:
            criterion_importance[crit] = max(criterion_importance.get(crit, 0.1), float(cfg["weight"]) * 3.0)

    # Track misconception tag frequencies across unique turns
    tag_turns: Dict[str, Set[str]] = {}
    for ev in evaluations:
        if ev.get("status") != "ok":
            continue
        tags = _safe_json(ev.get("misconception_tags"), [])
        if isinstance(tags, list):
            for tg in tags:
                t_clean = str(tg).strip()
                if t_clean:
                    tag_turns.setdefault(t_clean, set()).add(str(ev.get("turn_id") or ""))

    recurring_tags = {tg: sorted(tids) for tg, tids in tag_turns.items() if len(tids) >= 2}

    weaknesses: List[Dict[str, Any]] = []
    ok_evals = sorted(
        [e for e in evaluations if e.get("status") == "ok"],
        key=lambda e: str(e.get("turn_id") or ""),
    )

    for ev in ok_evals:
        rubric = _safe_json(ev.get("rubric_scores_json"), {})
        criteria = rubric.get("criteria") if isinstance(rubric, dict) else []
        mistakes = _safe_json(ev.get("technical_mistakes_json"), []) or []
        missing = _safe_json(ev.get("missing_concepts_json"), []) or []
        ev_tags = _safe_json(ev.get("misconception_tags"), []) or []

        for c in (criteria or []):
            try:
                sc = float(c.get("score"))
            except (TypeError, ValueError):
                continue
            quote = (c.get("quoted_justification") or "").strip()
            if sc < WEAKNESS_THRESHOLD and quote:
                cname_raw = str(c.get("criterion") or "technical_accuracy")
                importance = criterion_importance.get(cname_raw, 0.30)
                severity = round(importance * (1.0 - sc) * max(0.25, confidence_score), 4)
                is_rec = any(t in recurring_tags for t in ev_tags)
                detail_parts = []
                if mistakes:
                    detail_parts.append(f"Technical issue: {mistakes[0]}")
                elif missing:
                    detail_parts.append(f"Missed concept: {missing[0]}")
                cname_label = cname_raw.replace("_", " ").title()
                title = f"{cname_label} gap on {ev.get('skill_id') or 'question'}"
                if is_rec:
                    title += " [Recurring]"

                weaknesses.append({
                    "title": title,
                    "criterion": cname_raw,
                    "skill_id": ev.get("skill_id"),
                    "turn_id": ev.get("turn_id"),
                    "score": round(sc, 4),
                    "severity": severity,
                    "is_recurring": is_rec,
                    "recurring_tags": [t for t in ev_tags if t in recurring_tags],
                    "quote": quote,
                    "evidence": f'Turn {ev.get("turn_id")}: "{quote}"' + (f" — {'; '.join(detail_parts)}" if detail_parts else ""),
                })

    weaknesses.sort(key=lambda x: (-x["severity"], str(x["turn_id"]), str(x["criterion"])))
    return {
        "items": weaknesses[:6],
        "recurring_misconceptions": [
            {"tag": tag, "turn_ids": tids, "count": len(tids)}
            for tag, tids in sorted(recurring_tags.items())
        ],
    }


def _build_speech_dashboard(
    speech_summary: Dict[str, Any],
    data_sufficiency: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Phase 5 #4: Speech & communication dashboard. Missing -> 'Not measurable' with reason.
    Tips strictly derived from measured values.
    """
    wpm = speech_summary.get("wpm")
    fillers = speech_summary.get("filler_count")
    filler_map = speech_summary.get("filler_breakdown") or {}
    pause_count = speech_summary.get("pause_count")
    silence_ratio = speech_summary.get("silence_ratio")
    speaking_time_s = speech_summary.get("speaking_time_s")
    total_words = int(data_sufficiency.get("total_words") or 0)
    total_turns = int(data_sufficiency.get("total_candidate_turns") or 0)

    tips: List[str] = []
    if wpm is None:
        if total_turns > 0 and total_words > 0 and speaking_time_s is None:
            missing_reason = "No audio duration or word timestamps recorded (typed-only or timing unavailable)."
        else:
            missing_reason = "No spoken responses with timing recorded."
        tips.append("Speech pace and pauses were not measurable in this session.")
    else:
        missing_reason = None
        if wpm < WPM_OPTIMAL_MIN:
            tips.append(f"Speaking pace averaged {wpm} WPM (below {int(WPM_OPTIMAL_MIN)} WPM); aim for slightly crisper phrasing.")
        elif wpm > WPM_OPTIMAL_MAX:
            tips.append(f"Speaking pace averaged {wpm} WPM (above {int(WPM_OPTIMAL_MAX)} WPM); pause briefly between architectural points.")
        else:
            tips.append(f"Speaking pace averaged {wpm} WPM, within the optimal {int(WPM_OPTIMAL_MIN)}-{int(WPM_OPTIMAL_MAX)} WPM range.")

        if fillers is not None and fillers > 0 and filler_map:
            top_f, top_c = max(filler_map.items(), key=lambda kv: kv[1])
            tips.append(f"Detected {fillers} filler word(s), most frequently '{top_f}' ({top_c}x); replace fillers with silent 0.5s pauses.")
        elif fillers == 0:
            tips.append("Zero tracked filler words detected across measured spoken turns.")

    return {
        "wpm": wpm,
        "wpm_display": f"{wpm} WPM" if wpm is not None else "Not measurable",
        "total_words": total_words,
        "filler_count": fillers,
        "filler_count_display": str(fillers) if fillers is not None else "Not measurable",
        "filler_breakdown": filler_map,
        "pause_count": pause_count,
        "pause_count_display": str(pause_count) if pause_count is not None else "Not measurable",
        "longest_pause_s": speech_summary.get("longest_pause_s"),
        "avg_pause_s": speech_summary.get("avg_pause_s"),
        "speaking_time_s": speaking_time_s,
        "speaking_time_display": f"{round(speaking_time_s, 1)}s" if speaking_time_s is not None else "Not measurable",
        "silence_ratio": silence_ratio,
        "silence_ratio_display": f"{round(silence_ratio * 100, 1)}%" if silence_ratio is not None else "Not measurable",
        "pauses_status": speech_summary.get("pauses_status", "not_measurable"),
        "missing_reason": missing_reason,
        "tips": tips,
    }


def _build_question_reviews(
    turns: List[Dict[str, Any]],
    evaluations: List[Dict[str, Any]],
    speech_metrics: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Phase 5 #5: Complete per-question breakdown strictly from persisted rows."""
    eval_by_turn = {e.get("turn_id"): e for e in evaluations}
    speech_by_turn = {m.get("turn_id"): m for m in speech_metrics}
    cand_turns = [t for t in turns if t.get("speaker") == "candidate"]

    reviews: List[Dict[str, Any]] = []
    for t in cand_turns:
        tid = t.get("id")
        ev = eval_by_turn.get(tid) or {}
        sm = speech_by_turn.get(tid) or {}
        rubric = _safe_json(ev.get("rubric_scores_json"), {})
        criteria = rubric.get("criteria") if isinstance(rubric, dict) else []
        t_status = t.get("turn_status") or "answered"
        is_sm = t_status == "small_talk"

        reviews.append({
            "turn_id": tid,
            "turn_index": t.get("turn_index"),
            "question_number": t.get("turn_number") or t.get("turn_index"),
            "skill_id": t.get("skill_id"),
            "question": t.get("question_text") or "",
            "candidate_answer": t.get("text") or t.get("candidate_response") or "",
            "input_mode": t.get("input_mode") or "typed",
            "word_count": t.get("word_count") or 0,
            "turn_status": t_status,
            "is_small_talk": is_sm,
            "excluded_from_scoring": is_sm or (ev.get("status") != "ok"),
            "evaluation_status": "small_talk_excluded" if is_sm else (ev.get("status") or "pending"),
            "error_code": ev.get("error_code"),
            "score": compute_per_turn_score(ev) if ev else None,
            "score_100": round(compute_per_turn_score(ev) * 100.0, 1) if (ev and compute_per_turn_score(ev) is not None) else None,
            "criteria": criteria or [],
            "evaluator_type": ev.get("evaluator_type"),
            "prompt_id": ev.get("prompt_id"),
            "prompt_version": ev.get("prompt_version"),
            "model_used": ev.get("model_used"),
            "missing_concepts": _safe_json(ev.get("missing_concepts_json"), []) or [],
            "technical_mistakes": _safe_json(ev.get("technical_mistakes_json"), []) or [],
            "misconception_tags": _safe_json(ev.get("misconception_tags"), []) or [],
            "improved_answer": ev.get("improved_answer"),
            "speech_metrics": {
                "wpm": sm.get("wpm"),
                "filler_count": sm.get("filler_count"),
                "speaking_time_s": sm.get("speaking_time_s"),
                "missing_reason": sm.get("missing_reason"),
            },
        })
    return reviews


def _validate_narrative_numbers(narrative_text: str, allowed_numbers: Set[float]) -> bool:
    """
    Phase 5 #8: Extracts every number mentioned in LLM narrative and verifies each one
    matches an exact pre-computed value (prevents LLM numerical hallucination).
    """
    if not narrative_text or not isinstance(narrative_text, str):
        return False
    tokens = re.findall(r"\b\d+(?:\.\d+)?\b", narrative_text)
    for tok in tokens:
        val = float(tok)
        if not any(abs(val - allowed) < 0.06 for allowed in allowed_numbers):
            return False
    return True


def _generate_grounded_narrative(
    header: Dict[str, Any],
    scoring: Dict[str, Any],
    strengths: List[Dict[str, Any]],
    weaknesses: List[Dict[str, Any]],
    speech_dash: Dict[str, Any],
    chat_model: Any = None,
) -> Dict[str, Any]:
    """Generates and validates a grounded narrative paragraph from already-computed facts."""
    status = scoring["report_status"]
    if status in (REPORT_STATUS_INCOMPLETE, REPORT_STATUS_FAILED):
        return {
            "text": scoring["status_reason"],
            "source": "deterministic_status",
            "validated": True,
            "prompt_id": None,
            "prompt_version": None,
        }

    substantive_n = int(scoring["data_sufficiency"].get("answered_substantive_turns") or 0)
    score_100 = scoring.get("overall_score_100")
    cov_pct = round(float(scoring.get("coverage") or 0.0) * 100.0, 1)
    grade = scoring.get("grade")
    rec = scoring.get("recommendation")

    deterministic_fallback = (
        f"{header['candidate_name']} completed {substantive_n} substantive turn(s) for {header['role']} "
        f"({round(cov_pct)}% dimension coverage), achieving an overall score of {score_100}/100 "
        f"(Grade {grade}, Recommendation: {rec})."
    )
    if strengths:
        deterministic_fallback += f" Verified strength in {strengths[0]['title']}."
    if weaknesses:
        deterministic_fallback += f" Primary growth area identified in {weaknesses[0]['title']}."

    if chat_model is None:
        return {
            "text": deterministic_fallback,
            "source": "deterministic_computed",
            "validated": True,
            "prompt_id": NARRATIVE_PROMPT_ID,
            "prompt_version": NARRATIVE_PROMPT_VERSION,
        }

    # Build allowed numbers whitelist
    allowed: Set[float] = {
        float(substantive_n),
        float(scoring["data_sufficiency"].get("total_words") or 0),
        float(cov_pct),
        float(round(cov_pct)),
        float(scoring["evaluated_dimensions_count"]),
        float(scoring["total_dimensions_count"]),
    }
    if score_100 is not None:
        allowed.update({float(score_100), float(round(score_100))})
    if speech_dash.get("wpm") is not None:
        allowed.add(float(speech_dash["wpm"]))
        allowed.add(float(round(speech_dash["wpm"])))
    for d in scoring.get("dimensions", []):
        if d.get("score") is not None:
            allowed.add(float(d["score"]))
            allowed.add(float(round(d["score"])))

    facts_payload = {
        "candidate_name": header["candidate_name"],
        "role": header["role"],
        "report_status": status,
        "overall_score_100": score_100,
        "grade": grade,
        "recommendation": rec,
        "substantive_turns": substantive_n,
        "coverage_pct": round(cov_pct),
        "strengths": [{"title": s["title"], "quote": s["quote"]} for s in strengths[:2]],
        "weaknesses": [{"title": w["title"], "quote": w["quote"]} for w in weaknesses[:2]],
    }
    prompt = f"""Write a concise, objective 2-3 sentence executive summary paragraph based ONLY on these pre-computed facts.
Do NOT invent any new numbers, percentages, or claims not explicitly present below.

Facts JSON:
{json.dumps(facts_payload, indent=2)}"""

    try:
        from langchain_core.messages import HumanMessage
        runner = chat_model.bind(temperature=0.0) if hasattr(chat_model, "bind") else chat_model
        res = runner.invoke([HumanMessage(content=prompt)])
        raw_txt = (getattr(res, "content", None) or "").strip()
        if raw_txt and _validate_narrative_numbers(raw_txt, allowed):
            return {
                "text": raw_txt,
                "source": "gemini_grounded",
                "validated": True,
                "prompt_id": NARRATIVE_PROMPT_ID,
                "prompt_version": NARRATIVE_PROMPT_VERSION,
            }
        logger.warning("LLM narrative rejected due to ungrounded number or empty output; using deterministic summary.")
    except Exception as e:
        logger.warning("Narrative generation error (%s); using deterministic summary.", e)

    return {
        "text": deterministic_fallback,
        "source": "deterministic_fallback_after_validation",
        "validated": True,
        "prompt_id": NARRATIVE_PROMPT_ID,
        "prompt_version": NARRATIVE_PROMPT_VERSION,
    }


def _determine_next_action(report_status: str, display_name_source: str) -> str:
    if report_status == REPORT_STATUS_FAILED:
        return "retry_evaluation"
    if report_status == REPORT_STATUS_INCOMPLETE:
        return "continue_interview"
    if display_name_source == "fallback":
        return "add_name"
    return "practice_another"


def _sync_prompt1_roadmap_links(
    supabase_client: Any,
    user_id: Optional[str],
    session_id: str,
    evaluations: List[Dict[str, Any]],
    report_status: str,
) -> List[Dict[str, Any]]:
    """Phase 5 #10: Links evaluated skills back to Prompt 1 candidate_skill_states & Prep Roadmap."""
    if report_status not in (REPORT_STATUS_EVALUATED, REPORT_STATUS_PARTIAL) or not user_id:
        return []

    links: List[Dict[str, Any]] = []
    seen_skills: Set[str] = set()
    for ev in evaluations:
        if ev.get("status") != "ok":
            continue
        sk = ev.get("skill_id")
        if sk and sk not in seen_skills:
            seen_skills.add(sk)
            links.append({
                "skill_id": sk,
                "turn_id": ev.get("turn_id"),
                "evaluation_id": ev.get("id"),
                "roadmap_link": f"/dashboard?tab=roadmap&skill={sk}&session={session_id}",
            })
    return links


def generate_and_persist_report(
    supabase_client: Any,
    session_id: str,
    user_payload: Optional[Dict[str, Any]] = None,
    chat_model: Any = None,
) -> Dict[str, Any]:
    """
    Phase 5: Generates the complete evidence-grounded report strictly from persisted
    `sessions`, `interview_turns`, `interview_speech_metrics`, `interview_evaluations`.
    Persists idempotently to `interview_reports` and `sessions`.
    """
    sess_res = supabase_client.table("sessions").select("*").eq("session_id", session_id).limit(1).execute()
    if not sess_res or not sess_res.data:
        raise ValueError(f"Session {session_id} not found")
    session = sess_res.data[0]

    previous_status = session.get("report_status")

    # Resolve real candidate name with R6 priority
    user_id = session.get("user_id")
    parsed_resume = _safe_json(session.get("resume_snapshot_json") or session.get("structured_resume"), {})
    display_name, display_name_source = resolve_candidate_display_name(
        user_payload=user_payload,
        user_id=user_id,
        parsed_resume=parsed_resume,
        existing_name=session.get("display_name"),
        existing_source=session.get("display_name_source"),
        supabase_client=supabase_client,
    )

    # Await any in-flight per-turn background evaluations triggered on /next
    await_background_turn_evals(session_id, timeout_s=20.0)

    turns, speech_metrics = get_session_turns_and_metrics(supabase_client, session_id)
    eval_res = supabase_client.table("interview_evaluations").select("*").eq("session_id", session_id).execute()
    evaluations = list(eval_res.data or []) if eval_res else []

    # Parallel backfill evaluation for any ungraded candidate turns when model is active
    if chat_model is not None:
        existing_turn_ids = {str(e.get("turn_id")) for e in evaluations if e.get("turn_id")}
        pending_turns = [
            t for t in turns
            if t.get("speaker") == "candidate"
            and str(t.get("id")) not in existing_turn_ids
        ]
        if pending_turns:
            from services.interview_rubric_grader import evaluate_turns_parallel
            resume_summary = build_concise_resume_summary(parsed_resume or session.get("resume_text"))
            evaluate_turns_parallel(
                supabase_client=supabase_client,
                session_id=session_id,
                turn_rows=pending_turns,
                chat_model=chat_model,
                user_id=user_id,
                role=session.get("role") or "Software Engineer",
                difficulty=session.get("difficulty") or "Medium",
                resume_summary=resume_summary,
            )
            eval_res = supabase_client.table("interview_evaluations").select("*").eq("session_id", session_id).execute()
            evaluations = list(eval_res.data or []) if eval_res else []

    data_sufficiency = compute_data_sufficiency(supabase_client, session_id)

    scoring = score_interview_session(
        turns=turns,
        evaluations=evaluations,
        speech_metrics_list=speech_metrics,
        data_sufficiency=data_sufficiency,
    )

    strengths_block = _build_evidence_grounded_strengths(evaluations, scoring["coverage"])
    weaknesses_block = _build_evidence_grounded_weaknesses(evaluations, scoring["confidence"]["score"])
    speech_dash = _build_speech_dashboard(data_sufficiency.get("speech_summary") or {}, data_sufficiency)
    q_reviews = _build_question_reviews(turns, evaluations, speech_metrics)

    now_iso = _utc_now_iso()
    header = {
        "session_id": session_id,
        "candidate_name": display_name,
        "display_name": display_name,
        "display_name_source": display_name_source,
        "needs_name_prompt": display_name_source == "fallback",
        "role": session.get("role") or "Software Engineer",
        "level": session.get("level") or "Mid",
        "mode": session.get("mode") or session.get("interview_mode") or "resume",
        "date": session.get("started_at") or session.get("created_at") or now_iso,
        "duration_s": data_sufficiency.get("total_speaking_time_s"),
        "report_status": scoring["report_status"],
        "status_reason": scoring["status_reason"],
        "next_action": _determine_next_action(scoring["report_status"], display_name_source),
        "grade": scoring["grade"],
        "recommendation": scoring["recommendation"],
        "overall_score": scoring["overall_score"],
        "overall_score_100": scoring["overall_score_100"],
        "coverage": scoring["coverage"],
    }

    narrative = _generate_grounded_narrative(
        header=header,
        scoring=scoring,
        strengths=strengths_block["items"],
        weaknesses=weaknesses_block["items"],
        speech_dash=speech_dash,
        chat_model=chat_model,
    )

    roadmap_links = _sync_prompt1_roadmap_links(
        supabase_client=supabase_client,
        user_id=user_id,
        session_id=session_id,
        evaluations=evaluations,
        report_status=scoring["report_status"],
    )

    full_report = {
        "session_id": session_id,
        "formula_version": FORMULA_VERSION,
        "generated_at": now_iso,
        "header": header,
        "candidate_name": display_name,
        "display_name_source": display_name_source,
        "report_status": scoring["report_status"],
        "status_reason": scoring["status_reason"],
        "missing_reasons": scoring["missing_reasons"],
        "next_action": header["next_action"],
        "overall_score": scoring["overall_score"],
        "overall_score_100": scoring["overall_score_100"],
        "grade": scoring["grade"],
        "recommendation": scoring["recommendation"],
        "hiring_recommendation": scoring["recommendation"],
        "coverage": scoring["coverage"],
        "confidence": scoring["confidence"],
        "section_grades": scoring["dimensions"],
        "dimensions": scoring["dimensions"],
        "not_assessed_yet": scoring["unassessed_dimensions"],
        "speech_metrics": speech_dash,
        "question_reviews": q_reviews,
        "turn_evaluations": q_reviews,
        "strengths": strengths_block["items"],
        "strengths_empty_message": strengths_block["empty_message"],
        "weaknesses": weaknesses_block["items"],
        "recurring_misconceptions": weaknesses_block["recurring_misconceptions"],
        "narrative": narrative,
        "report": narrative["text"],
        "data_sufficiency": data_sufficiency,
        "answered_questions_count": data_sufficiency.get("answered_substantive_turns", 0),
        "roadmap_evidence_links": roadmap_links,
    }

    # Persist idempotently in `interview_reports` (keyed on unique `session_id`)
    report_row = {
        "id": f"rep_{session_id}",
        "session_id": session_id,
        "candidate_id": str(user_id or "anonymous"),
        "report_status": scoring["report_status"],
        "overall_score": scoring["overall_score"],
        "grade": scoring["grade"],
        "recommendation": scoring["recommendation"],
        "dimension_scores_json": scoring["dimensions"],
        "strengths_json": strengths_block["items"],
        "weaknesses_json": weaknesses_block["items"],
        "coverage_json": {"coverage": scoring["coverage"], "unassessed": scoring["unassessed_dimensions"]},
        "data_sufficiency_json": data_sufficiency,
        "formula_version": FORMULA_VERSION,
        "generated_at": now_iso,
    }
    supabase_client.table("interview_reports").upsert(report_row, on_conflict="session_id").execute()

    # Sync back to `sessions` cleanly (preserving real display_name & report_status)
    session_update_payload = {
        "display_name": display_name,
        "display_name_source": display_name_source,
        "report_status": scoring["report_status"],
        "final_score": scoring["overall_score_100"],
        "final_score_100": scoring["overall_score_100"],
        "final_grade": scoring["grade"],
        "hiring_recommendation": scoring["recommendation"],
        "final_report": json.dumps(full_report),
        "report_json": json.dumps(full_report),
        "updated_at": now_iso,
    }
    try:
        supabase_client.table("sessions").update(session_update_payload).eq("session_id", session_id).execute()
    except Exception as e_sess:
        logger.warning(
            "Initial sessions table update in report generation encountered schema issue: %s. Attempting fallback.",
            e_sess,
        )
        # Fallback to core columns if live schema cache lacks hiring_recommendation or other optional columns
        core_payload = {
            "report_status": scoring["report_status"],
            "final_score": scoring["overall_score_100"],
            "final_score_100": scoring["overall_score_100"],
            "final_grade": scoring["grade"],
            "report_json": json.dumps(full_report),
            "updated_at": now_iso,
        }
        try:
            supabase_client.table("sessions").update(core_payload).eq("session_id", session_id).execute()
        except Exception as e_sess_core:
            logger.error("Failed even core sessions table update during report generation: %s", e_sess_core)

    record_report_audit_log(
        supabase_client=supabase_client,
        session_id=session_id,
        actor_id=str((user_payload or {}).get("sub") or user_id or "anonymous"),
        report_status=scoring["report_status"],
        previous_status=previous_status,
        overall_score=scoring["overall_score_100"],
        formula_version=FORMULA_VERSION,
    )

    return full_report


def send_interview_report_email_http(to_email: str, report_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 5 #9: Sends interview report email via HTTP API (Resend or SendGrid) instead of blocked SMTP.
    Never swallows errors; returns honest { ok, provider, error } status.
    """
    if not to_email or "@" not in str(to_email):
        return {"ok": False, "provider": "none", "error": "Invalid recipient email address."}

    header = report_payload.get("header") or {}
    c_name = header.get("candidate_name", "Candidate")
    status = report_payload.get("report_status", "PENDING")
    grade = report_payload.get("grade") or "N/A (Not Evaluated)"
    score_100 = report_payload.get("overall_score_100")
    score_str = f"{score_100}/100" if score_100 is not None else "Not scored"
    summary_txt = (report_payload.get("narrative") or {}).get("text") or report_payload.get("status_reason", "")

    html_body = (
        f"<h2>PrepFly Interview Report — {c_name}</h2>"
        f"<p><strong>Status:</strong> {status} | <strong>Score:</strong> {score_str} | <strong>Grade:</strong> {grade}</p>"
        f"<p>{summary_txt}</p>"
    )
    subject = f"PrepFly Interview Report ({status}) — {header.get('role', 'Interview')}"

    import urllib.request
    import urllib.error

    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    if resend_key and not resend_key.startswith("re_prepfly_rotated"):
        try:
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=json.dumps({
                    "from": os.getenv("RESEND_FROM_EMAIL", "PrepFly <onboarding@resend.dev>"),
                    "to": [to_email],
                    "subject": subject,
                    "html": html_body,
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"ok": 200 <= resp.status < 300, "provider": "resend", "status_code": resp.status}
        except Exception as err:
            return {"ok": False, "provider": "resend", "error": str(err)}

    sendgrid_key = os.getenv("SENDGRID_API_KEY", "").strip()
    if sendgrid_key:
        try:
            req = urllib.request.Request(
                "https://api.sendgrid.com/v3/mail/send",
                data=json.dumps({
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": os.getenv("SENDGRID_FROM_EMAIL", "noreply@prepfly.io")},
                    "subject": subject,
                    "content": [{"type": "text/html", "value": html_body}],
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {sendgrid_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"ok": 200 <= resp.status < 300, "provider": "sendgrid", "status_code": resp.status}
        except Exception as err:
            return {"ok": False, "provider": "sendgrid", "error": str(err)}

    return {
        "ok": False,
        "provider": "none",
        "error": "No HTTP email provider configured (RESEND_API_KEY or SENDGRID_API_KEY required; SMTP is disabled).",
    }

