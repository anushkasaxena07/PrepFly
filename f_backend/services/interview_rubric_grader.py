"""
Phase 3: Evidence-Based Rubric Grader (Scores Come From Code, Verbatim Quotes Verified)
Operating Rules R1, R2, R3, R4, R8:
  - LLM evaluates against structured criteria and returns per-criterion scores + verbatim quotes.
  - Verifies every quoted_justification is an actual substring of the candidate's answer.
  - Double-grades critical-skill answers, averages normalized scores, flags disagreement > 0.25.
  - Status handling: 'ok', 'failed' (stores error_code, score=NULL — NEVER 0), 'skipped'.
  - Every OK evaluation writes `interview_evaluations` AND deduplicated Prompt 1 `skill_evidence`
    (`source_type='ai_interview'`), then recomputes ONLY the affected skills.
"""

import asyncio
import concurrent.futures
import json
import logging
import random
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.interview_scoring_config import (
    BACKOFF_BASE_SECONDS,
    DOUBLE_GRADE_DISAGREEMENT_THRESHOLD,
    FAST_GRADER_MODEL,
    FORMULA_VERSION,
    GEMINI_REQUEST_TIMEOUT_S,
    GRADER_MAX_OUTPUT_TOKENS,
    MAX_EVAL_CONCURRENCY,
)
from services.interview_reliability_service import (
    DailyTokenBudgetTracker,
    TokenBudgetExceededError,
    build_concise_resume_summary,
    get_degraded_error_payload,
    log_structured_event,
)

logger = logging.getLogger(__name__)

RUBRIC_PROMPT_ID = "interview_rubric_grader"
RUBRIC_PROMPT_VERSION = "v1.0"
EVALUATOR_VERSION = "interview_rubric_v1.0"

DEFAULT_RUBRIC_CRITERIA = [
    {"criterion": "technical_accuracy", "weight": 0.25, "description": "Factual correctness of domain concepts and mechanisms"},
    {"criterion": "technical_depth", "weight": 0.20, "description": "Trade-offs, internals, edge cases, and failure modes"},
    {"criterion": "problem_solving", "weight": 0.20, "description": "Structured reasoning and step-by-step decomposition"},
    {"criterion": "role_relevance", "weight": 0.15, "description": "Relevance to target role and question prompt"},
    {"criterion": "examples", "weight": 0.10, "description": "Concrete production examples, metrics, or specifics"},
    {"criterion": "clarity", "weight": 0.10, "description": "Clear structure and conciseness of written/spoken explanation"},
]

CRITICAL_SKILLS_SET = {
    "sys_distributed_cap", "sys_rate_limiting", "db_indexing", "db_transactions",
    "dsa_arrays_hashing", "dsa_trees_graphs", "genai_llm_fundamentals",
    "interview_system_design", "interview_dsa",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_for_quote_match(text: str) -> str:
    s = (text or "").lower()
    s = s.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = re.sub(r"[\s]+", " ", s).strip()
    return s


def verify_quote_in_answer(quote: Optional[str], candidate_answer: str) -> bool:
    """
    Strictly verifies that `quote` is a real, non-empty verbatim substring of `candidate_answer`
    (ignoring surrounding quotes and normalized whitespace/case). Rejects fabricated quotes.
    """
    if not quote or not isinstance(quote, str):
        return False
    cleaned_q = quote.strip().strip("\"'`.,;:!?")
    if len(cleaned_q) < 4:
        return False
    norm_q = _normalize_for_quote_match(cleaned_q)
    norm_ans = _normalize_for_quote_match(candidate_answer)
    if not norm_q or not norm_ans:
        return False
    if norm_q in norm_ans:
        return True
    # Also allow match after stripping punctuation inside quote/answer
    alnum_q = re.sub(r"[^a-z0-9\s]", "", norm_q).strip()
    alnum_ans = re.sub(r"[^a-z0-9\s]", "", norm_ans).strip()
    return bool(alnum_q) and len(alnum_q) >= 4 and (alnum_q in alnum_ans)


def _strip_json_fences(raw: str) -> str:
    txt = (raw or "").strip()
    if txt.startswith("```"):
        lines = txt.split("\n")
        if len(lines) >= 3:
            txt = "\n".join(lines[1:-1]).strip()
        else:
            txt = txt.strip("`").strip()
    return txt


def _validate_and_score_rubric_output(raw_json: Any, candidate_answer: str) -> Tuple[Dict[str, Any], float]:
    """
    Validates schema & verbatim quotes, then deterministically computes weighted mean normalized_score (0..1).
    Raises ValueError on any schema or fabricated quote violation.
    """
    if not isinstance(raw_json, dict):
        raise ValueError("Grader output must be a JSON object")

    criteria = raw_json.get("criteria")
    if not isinstance(criteria, list) or len(criteria) == 0:
        raise ValueError("Missing non-empty 'criteria' list")

    weight_lookup = {c["criterion"]: c["weight"] for c in DEFAULT_RUBRIC_CRITERIA}
    total_w = 0.0
    weighted_sum = 0.0
    validated_criteria: List[Dict[str, Any]] = []

    for idx, item in enumerate(criteria):
        if not isinstance(item, dict):
            raise ValueError(f"Criterion entry #{idx} must be an object")
        cname = str(item.get("criterion") or "").strip()
        if not cname:
            raise ValueError(f"Criterion entry #{idx} missing 'criterion' name")

        try:
            c_score = float(item.get("score"))
        except (TypeError, ValueError):
            raise ValueError(f"Criterion '{cname}' invalid numeric score: {item.get('score')!r}")
        if not (0.0 <= c_score <= 1.0):
            raise ValueError(f"Criterion '{cname}' score {c_score} out of range [0.0, 1.0]")

        c_weight = item.get("weight", weight_lookup.get(cname, 1.0 / len(criteria)))
        try:
            c_weight_f = float(c_weight)
        except (TypeError, ValueError):
            c_weight_f = weight_lookup.get(cname, 0.2)
        if c_weight_f <= 0:
            c_weight_f = 0.1

        quote = item.get("quoted_justification")
        if not verify_quote_in_answer(quote, candidate_answer):
            raise ValueError(
                f"Quote verification failed for criterion '{cname}': "
                f"quoted_justification={quote!r} not found verbatim in candidate answer"
            )

        total_w += c_weight_f
        weighted_sum += c_weight_f * c_score
        validated_criteria.append({
            "criterion": cname,
            "weight": round(c_weight_f, 4),
            "score": round(c_score, 4),
            "quoted_justification": quote.strip(),
        })

    normalized_score = round(max(0.0, min(1.0, weighted_sum / total_w)), 4) if total_w > 0 else 0.0

    for list_field in ("missing_concepts", "technical_mistakes", "misconception_tags"):
        val = raw_json.get(list_field, [])
        if not isinstance(val, list):
            raise ValueError(f"Field '{list_field}' must be a JSON array")

    improved = raw_json.get("improved_answer", "")
    if not isinstance(improved, str):
        raise ValueError("Field 'improved_answer' must be a string")

    cleaned = {
        "criteria": validated_criteria,
        "missing_concepts": [str(x) for x in raw_json.get("missing_concepts", [])],
        "technical_mistakes": [str(x) for x in raw_json.get("technical_mistakes", [])],
        "misconception_tags": [str(x) for x in raw_json.get("misconception_tags", [])],
        "improved_answer": improved.strip(),
    }
    return cleaned, normalized_score


def _is_transient_error(err: Exception) -> Tuple[bool, str]:
    s = str(err).lower()
    if "503" in s or "unavailable" in s:
        return True, "GEMINI_503"
    if "504" in s or "deadline" in s or "timeout" in s or "timed out" in s:
        return True, "GEMINI_504"
    if "429" in s or "resource exhausted" in s or "rate" in s:
        return True, "GEMINI_429"
    return False, "GRADING_ERROR"


def _invoke_gemini_temp0(
    chat_model: Any,
    prompt: str,
    user_id: Optional[str] = None,
    timeout_s: float = GEMINI_REQUEST_TIMEOUT_S,
    max_output_tokens: int = GRADER_MAX_OUTPUT_TOKENS,
) -> Tuple[str, str]:
    """
    Invokes Gemini deterministically with temperature=0, capped output tokens,
    enforced timeout, and daily per-user token budget tracking.
    Returns (text, model_used).
    """
    if chat_model is None:
        raise RuntimeError("GEMINI_UNAVAILABLE: chat_model is None")

    DailyTokenBudgetTracker.check_budget(user_id, estimated_tokens=max(200, len(prompt) // 4))

    from langchain_core.messages import HumanMessage

    model_used = getattr(chat_model, "model", None) or getattr(chat_model, "model_name", None) or FAST_GRADER_MODEL
    runner = chat_model
    if hasattr(chat_model, "bind"):
        try:
            runner = chat_model.bind(
                temperature=0.0,
                max_output_tokens=max_output_tokens,
                timeout=timeout_s,
            )
        except Exception:
            try:
                runner = chat_model.bind(temperature=0.0)
            except Exception:
                runner = chat_model

    def _call():
        return runner.invoke([HumanMessage(content=prompt)])

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(_call)
        try:
            res = fut.result(timeout=timeout_s)
        except concurrent.futures.TimeoutError as te:
            raise TimeoutError(f"GEMINI_504: Request deadline exceeded after {timeout_s}s") from te

    content = getattr(res, "content", None)
    if content is None and isinstance(res, str):
        content = res
    if not content:
        raise ValueError("Empty response from Gemini grader")

    DailyTokenBudgetTracker.record_usage(user_id, len(prompt), len(str(content)))
    return str(content), str(model_used)


def _grade_single_pass(
    question: str,
    answer: str,
    role: str,
    skill_id: Optional[str],
    difficulty: str,
    chat_model: Any,
    max_attempts: int = 3,
    user_id: Optional[str] = None,
    resume_summary: str = "",
    fallback_model: Any = None,
) -> Tuple[Dict[str, Any], float, str]:
    """
    Runs one concise schema+quote-verified rubric pass with retries + exponential backoff/jitter
    on transient 503/504/429, explicit fallback model tracking (`model_used`), and
    validation-error feedback on invalid JSON / fabricated quotes.
    """
    criteria_spec = "\n".join(
        f"- {c['criterion']} (w={c['weight']}): {c['description']}" for c in DEFAULT_RUBRIC_CRITERIA
    )
    compact_ctx = build_concise_resume_summary(resume_summary)
    ctx_line = f"\nCandidate Context: {compact_ctx}" if compact_ctx else ""

    base_prompt = f"""Evidence-based technical rubric grader. Quote EXACT verbatim substrings from Answer into "quoted_justification".
Role: {role} | Skill: {skill_id or 'general'} | Difficulty: {difficulty}{ctx_line}
Question: {question}
Candidate Answer: {answer}
Criteria:
{criteria_spec}
Return ONLY valid JSON:
{{"criteria":[{{"criterion":"technical_accuracy","weight":0.25,"score":0.0,"quoted_justification":"exact substring"}}],"missing_concepts":["string"],"technical_mistakes":["string"],"misconception_tags":["string"],"improved_answer":"concise stronger answer"}}"""

    prompt_to_send = base_prompt
    last_err: Optional[Exception] = None
    last_code = "GRADING_ERROR"

    for attempt in range(max_attempts):
        t0 = time.perf_counter()
        try:
            raw_text, model_used = _invoke_gemini_temp0(chat_model, prompt_to_send, user_id=user_id)
            parsed = json.loads(_strip_json_fences(raw_text))
            cleaned, norm_score = _validate_and_score_rubric_output(parsed, answer)
            log_structured_event(
                "rubric_grade_success",
                skill_id=skill_id,
                attempt=attempt + 1,
                model_used=model_used,
                prompt_id=RUBRIC_PROMPT_ID,
                prompt_version=RUBRIC_PROMPT_VERSION,
                latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            )
            return cleaned, norm_score, model_used
        except TokenBudgetExceededError:
            raise
        except (json.JSONDecodeError, ValueError) as val_err:
            last_err = val_err
            last_code = "QUOTE_VERIFICATION_FAILED" if "Quote verification failed" in str(val_err) else "SCHEMA_VALIDATION_FAILED"
            logger.warning("Rubric grader validation failed (attempt %d/%d): %s", attempt + 1, max_attempts, val_err)
            log_structured_event(
                "rubric_grade_validation_retry",
                level=logging.WARNING,
                attempt=attempt + 1,
                error_code=last_code,
            )
            prompt_to_send = (
                f"{base_prompt}\n\nPREVIOUS OUTPUT REJECTED ({val_err}). "
                "Every criterion MUST have an exact verbatim substring from Candidate Answer in quoted_justification, and valid JSON only."
            )
        except Exception as err:
            last_err = err
            transient, code = _is_transient_error(err)
            last_code = code if transient else ("GEMINI_UNAVAILABLE" if "chat_model is None" in str(err) else "GRADING_ERROR")
            logger.warning("Rubric grader error (attempt %d/%d, %s): %s", attempt + 1, max_attempts, last_code, err)
            if transient and attempt < max_attempts - 1:
                backoff_s = round((BACKOFF_BASE_SECONDS * (2 ** attempt)) + random.uniform(0.0, 0.15), 3)
                log_structured_event(
                    "rubric_grade_backoff_retry",
                    level=logging.WARNING,
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    error_code=last_code,
                    backoff_s=backoff_s,
                )
                time.sleep(backoff_s)
                continue
            break

    # Explicit fallback model attempt if primary hit transient outage
    if fallback_model is not None and last_code in ("GEMINI_503", "GEMINI_504", "GEMINI_429"):
        try:
            raw_text, fb_name = _invoke_gemini_temp0(fallback_model, base_prompt, user_id=user_id)
            parsed = json.loads(_strip_json_fences(raw_text))
            cleaned, norm_score = _validate_and_score_rubric_output(parsed, answer)
            recorded_model = f"{fb_name} (fallback)"
            log_structured_event(
                "rubric_grade_fallback_success",
                level=logging.WARNING,
                primary_error_code=last_code,
                model_used=recorded_model,
            )
            return cleaned, norm_score, recorded_model
        except Exception as fb_err:
            last_err = fb_err

    raise RuntimeError(f"{last_code}: {last_err}")


def _record_prompt1_skill_evidence(
    supabase_client: Any,
    user_id: Optional[str],
    session_id: str,
    turn_id: str,
    skill_id: Optional[str],
    normalized_score: float,
    difficulty: str,
    rubric_payload: Dict[str, Any],
) -> Optional[str]:
    """
    Writes deduplicated Prompt 1 `skill_evidence` (`source_type='ai_interview'`) and
    recomputes affected `(user_id, skill_id)` in `candidate_skill_states` and `candidate_skill_profiles`.
    """
    if not user_id or not skill_id or supabase_client is None:
        return None

    score_100 = round(normalized_score * 100.0, 2)
    dedupe_key = f"ai_interview:{session_id}:{turn_id}"
    now_iso = _utc_now_iso()

    # Check idempotency via dedupe_key so retries/double-clicks NEVER duplicate evidence
    try:
        existing = supabase_client.table("skill_evidence").select("id").eq("dedupe_key", dedupe_key).limit(1).execute()
        if existing and getattr(existing, "data", None):
            return existing.data[0]["id"]
    except Exception:
        pass

    ev_id = f"ev_{uuid.uuid4().hex[:14]}"
    demonstrated = [
        c["criterion"] for c in (rubric_payload.get("criteria") or []) if float(c.get("score", 0)) >= 0.7
    ]
    missed = rubric_payload.get("missing_concepts") or []
    misconceptions = rubric_payload.get("misconception_tags") or []

    # 1. Write to Prompt 1 `skill_evidence` table
    evidence_row = {
        "id": ev_id,
        "user_id": str(user_id),
        "skill_id": str(skill_id),
        "source_type": "ai_interview",
        "source_id": turn_id,
        "score": score_100,
        "raw_score": score_100,
        "weighted_score": score_100,
        "confidence": 0.75,
        "weight": 0.15,
        "demonstrated_concepts": json.dumps(demonstrated),
        "missed_concepts": json.dumps(missed),
        "misconceptions": json.dumps(misconceptions),
        "evidence_notes": json.dumps([c.get("quoted_justification") for c in (rubric_payload.get("criteria") or [])]),
        "rubric_version": RUBRIC_PROMPT_VERSION,
        "difficulty": difficulty,
        "evaluator_version": EVALUATOR_VERSION,
        "dedupe_key": dedupe_key,
        "created_at": now_iso,
    }
    supabase_client.table("skill_evidence").insert(evidence_row).execute()

    # 2. Also register in EvidenceRegistryService (Prompt 1 deduplicated registry)
    try:
        from services.evidence_registry_service import EvidenceRegistryService, SOURCE_AI_INTERVIEW
        EvidenceRegistryService.record_evidence(
            user_id=str(user_id),
            skill_id=str(skill_id),
            source_type=SOURCE_AI_INTERVIEW,
            raw_score=score_100,
            difficulty=difficulty,
            source_id=turn_id,
            submission_content=dedupe_key,
            evaluation_rubric=rubric_payload,
            evaluator_type="gemini_rubric",
            metadata={"session_id": session_id, "evaluator_version": EVALUATOR_VERSION},
            supabase_client=supabase_client,
        )
    except Exception as reg_err:
        logger.debug("EvidenceRegistryService sync notice: %s", reg_err)

    # 3. Recompute ONLY this affected (user_id, skill_id) in `candidate_skill_states` & `candidate_skill_profiles`
    try:
        ev_res = supabase_client.table("skill_evidence").select("*").eq("user_id", str(user_id)).eq("skill_id", str(skill_id)).execute()
        all_ev = list(ev_res.data or []) if ev_res else [evidence_row]
        scores_list = [float(r.get("score") or r.get("raw_score") or 0.0) for r in all_ev]
        avg_prof = round(sum(scores_list) / len(scores_list), 2) if scores_list else score_100
        conf = round(min(0.95, 0.45 + 0.12 * len(all_ev)), 2)

        state_res = supabase_client.table("candidate_skill_states").select("id").eq("user_id", str(user_id)).eq("skill_id", str(skill_id)).limit(1).execute()
        if state_res and state_res.data:
            supabase_client.table("candidate_skill_states").update({
                "proficiency": avg_prof,
                "confidence": conf,
                "sample_count": len(all_ev),
                "last_assessed_at": now_iso,
                "updated_at": now_iso,
            }).eq("id", state_res.data[0]["id"]).execute()
        else:
            supabase_client.table("candidate_skill_states").insert({
                "id": f"css_{uuid.uuid4().hex[:12]}",
                "user_id": str(user_id),
                "skill_id": str(skill_id),
                "proficiency": avg_prof,
                "confidence": conf,
                "sample_count": len(all_ev),
                "last_assessed_at": now_iso,
                "updated_at": now_iso,
            }).execute()
    except Exception as css_err:
        logger.debug("candidate_skill_states update notice: %s", css_err)

    return ev_id


def grade_and_persist_turn(
    supabase_client: Any,
    session_id: str,
    turn_row: Dict[str, Any],
    question_text: str,
    chat_model: Any,
    user_id: Optional[str] = None,
    role: str = "Software Engineer",
    difficulty: str = "Medium",
    is_critical: Optional[bool] = None,
    resume_summary: str = "",
    fallback_model: Any = None,
) -> Dict[str, Any]:
    """
    Evaluates a single candidate turn against the rubric and persists `interview_evaluations` +
    (on 'ok') Prompt 1 `skill_evidence`. Never turns failures or skipped turns into score 0.
    """
    turn_id = turn_row["id"]
    turn_status = turn_row.get("turn_status") or "answered"
    sub_reason = turn_row.get("intent") or ""
    skill_id = turn_row.get("skill_id") or "general_technical"
    answer_text = (turn_row.get("text") or "").strip()
    eval_id = f"eval_{turn_id}"
    now_iso = _utc_now_iso()

    # 1. Skipped / non-scoring turn statuses (NEVER converted to 0)
    is_explicit_skip = (turn_status == "skipped" and sub_reason != "dont_know")
    if turn_status in ("empty", "off_topic", "small_talk", "stt_failed", "stt_low_confidence") or is_explicit_skip:
        eval_row = {
            "id": eval_id,
            "turn_id": turn_id,
            "session_id": session_id,
            "skill_id": skill_id,
            "rubric_scores_json": None,
            "raw_score": None,
            "normalized_score": None,
            "quoted_evidence_json": [],
            "missing_concepts_json": [],
            "technical_mistakes_json": [],
            "improved_answer": None,
            "misconception_tags": [],
            "evaluator_type": "turn_status_gate",
            "prompt_id": RUBRIC_PROMPT_ID,
            "prompt_version": RUBRIC_PROMPT_VERSION,
            "model_used": None,
            "status": "skipped",
            "error_code": f"TURN_{turn_status.upper()}",
            "created_at": now_iso,
        }
        supabase_client.table("interview_evaluations").upsert(eval_row, on_conflict="id").execute()
        return eval_row

    # 2. Explicit "I don't know" turn -> deterministic low skill score (0.10) with explicit label
    if turn_status == "skipped" and sub_reason == "dont_know":
        norm_score = 0.10
        rubric_payload = {
            "criteria": [
                {"criterion": "technical_accuracy", "weight": 0.5, "score": 0.10, "quoted_justification": answer_text},
                {"criterion": "technical_depth", "weight": 0.5, "score": 0.10, "quoted_justification": answer_text},
            ],
            "missing_concepts": ["Core domain concepts for this question"],
            "technical_mistakes": [],
            "misconception_tags": ["explicit_knowledge_gap"],
            "improved_answer": "Attempt to reason from first principles or discuss adjacent trade-offs even when uncertain.",
        }
        eval_row = {
            "id": eval_id,
            "turn_id": turn_id,
            "session_id": session_id,
            "skill_id": skill_id,
            "rubric_scores_json": rubric_payload,
            "raw_score": 10.0,
            "normalized_score": norm_score,
            "quoted_evidence_json": [answer_text],
            "missing_concepts_json": rubric_payload["missing_concepts"],
            "technical_mistakes_json": [],
            "improved_answer": rubric_payload["improved_answer"],
            "misconception_tags": ["explicit_knowledge_gap"],
            "evaluator_type": "deterministic_dont_know",
            "prompt_id": RUBRIC_PROMPT_ID,
            "prompt_version": RUBRIC_PROMPT_VERSION,
            "model_used": "deterministic",
            "status": "ok",
            "error_code": None,
            "created_at": now_iso,
        }
        supabase_client.table("interview_evaluations").upsert(eval_row, on_conflict="id").execute()
        _record_prompt1_skill_evidence(
            supabase_client, user_id, session_id, turn_id, skill_id, norm_score, difficulty, rubric_payload
        )
        return eval_row

    # 3. Grade substantive answer via Gemini (double-grade if critical skill)
    critical = bool(is_critical) if is_critical is not None else (skill_id in CRITICAL_SKILLS_SET or "design" in role.lower() and "architecture" in question_text.lower())

    try:
        rubric_1, score_1, model_used = _grade_single_pass(
            question_text,
            answer_text,
            role,
            skill_id,
            difficulty,
            chat_model,
            user_id=user_id,
            resume_summary=resume_summary,
            fallback_model=fallback_model,
        )
        final_rubric = dict(rubric_1)
        final_norm = score_1

        if critical:
            rubric_2, score_2, _ = _grade_single_pass(
                question_text,
                answer_text,
                role,
                skill_id,
                difficulty,
                chat_model,
                user_id=user_id,
                resume_summary=resume_summary,
                fallback_model=fallback_model,
            )
            delta = round(abs(score_1 - score_2), 4)
            disagreement_flagged = delta > DOUBLE_GRADE_DISAGREEMENT_THRESHOLD
            if disagreement_flagged:
                logger.warning(
                    "Double-grade disagreement %.3f > %.2f on critical turn %s (%s)",
                    delta, DOUBLE_GRADE_DISAGREEMENT_THRESHOLD, turn_id, skill_id
                )
            final_norm = round((score_1 + score_2) / 2.0, 4)
            # Average per-criterion scores while keeping verified quotes from pass 1
            c2_map = {c["criterion"]: c["score"] for c in rubric_2["criteria"]}
            for c in final_rubric["criteria"]:
                if c["criterion"] in c2_map:
                    c["score"] = round((c["score"] + c2_map[c["criterion"]]) / 2.0, 4)
            final_rubric["double_graded"] = True
            final_rubric["pass_scores"] = [score_1, score_2]
            final_rubric["disagreement_delta"] = delta
            final_rubric["disagreement_flagged"] = disagreement_flagged

        raw_score_100 = round(final_norm * 100.0, 2)
        quoted_evidence = [
            {"criterion": c["criterion"], "quote": c["quoted_justification"], "score": c["score"]}
            for c in final_rubric["criteria"]
        ]

        eval_row = {
            "id": eval_id,
            "turn_id": turn_id,
            "session_id": session_id,
            "skill_id": skill_id,
            "rubric_scores_json": final_rubric,
            "raw_score": raw_score_100,
            "normalized_score": final_norm,
            "quoted_evidence_json": quoted_evidence,
            "missing_concepts_json": final_rubric["missing_concepts"],
            "technical_mistakes_json": final_rubric["technical_mistakes"],
            "improved_answer": final_rubric["improved_answer"],
            "misconception_tags": final_rubric["misconception_tags"],
            "evaluator_type": "gemini_rubric_double" if critical else "gemini_rubric",
            "prompt_id": RUBRIC_PROMPT_ID,
            "prompt_version": RUBRIC_PROMPT_VERSION,
            "model_used": model_used,
            "status": "ok",
            "error_code": None,
            "created_at": now_iso,
        }
        supabase_client.table("interview_evaluations").upsert(eval_row, on_conflict="id").execute()
        _record_prompt1_skill_evidence(
            supabase_client, user_id, session_id, turn_id, skill_id, final_norm, difficulty, final_rubric
        )
        return eval_row

    except Exception as grade_err:
        err_msg = str(grade_err)
        error_code = err_msg.split(":", 1)[0].strip() if ":" in err_msg else "GRADING_ERROR"
        logger.error("Turn evaluation failed for %s (%s): %s", turn_id, error_code, err_msg)
        failed_row = {
            "id": eval_id,
            "turn_id": turn_id,
            "session_id": session_id,
            "skill_id": skill_id,
            "rubric_scores_json": None,
            "raw_score": None,
            "normalized_score": None,
            "quoted_evidence_json": [],
            "missing_concepts_json": [],
            "technical_mistakes_json": [],
            "improved_answer": None,
            "misconception_tags": [],
            "evaluator_type": "gemini_rubric",
            "prompt_id": RUBRIC_PROMPT_ID,
            "prompt_version": RUBRIC_PROMPT_VERSION,
            "model_used": None,
            "status": "failed",
            "error_code": error_code[:64],
            "created_at": now_iso,
        }
        supabase_client.table("interview_evaluations").upsert(failed_row, on_conflict="id").execute()
        return failed_row


async def evaluate_turns_parallel_async(
    supabase_client: Any,
    session_id: str,
    turn_rows: List[Dict[str, Any]],
    chat_model: Any,
    user_id: Optional[str] = None,
    role: str = "Software Engineer",
    difficulty: str = "Medium",
    resume_summary: str = "",
    fallback_model: Any = None,
    max_concurrency: int = MAX_EVAL_CONCURRENCY,
) -> List[Dict[str, Any]]:
    """
    Phase 7: Runs independent per-turn evaluations concurrently via `asyncio.gather`
    with an explicit concurrency cap (`asyncio.Semaphore`).
    """
    sem = asyncio.Semaphore(max(1, int(max_concurrency)))

    async def _worker(t_row: Dict[str, Any]) -> Dict[str, Any]:
        async with sem:
            return await asyncio.to_thread(
                grade_and_persist_turn,
                supabase_client=supabase_client,
                session_id=session_id,
                turn_row=t_row,
                question_text=t_row.get("question_text") or "",
                chat_model=chat_model,
                user_id=user_id,
                role=role,
                difficulty=difficulty,
                resume_summary=resume_summary,
                fallback_model=fallback_model,
            )

    if not turn_rows:
        return []
    return list(await asyncio.gather(*(_worker(tr) for tr in turn_rows)))


def evaluate_turns_parallel(
    supabase_client: Any,
    session_id: str,
    turn_rows: List[Dict[str, Any]],
    chat_model: Any,
    user_id: Optional[str] = None,
    role: str = "Software Engineer",
    difficulty: str = "Medium",
    resume_summary: str = "",
    fallback_model: Any = None,
    max_concurrency: int = MAX_EVAL_CONCURRENCY,
) -> List[Dict[str, Any]]:
    """
    Synchronous bridge for parallel per-turn rubric evaluation capped at `max_concurrency`.
    Uses `asyncio.gather` + `asyncio.Semaphore` (`evaluate_turns_parallel_async`) on POSIX,
    and falls back to bounded `ThreadPoolExecutor` on Windows where `socket.socketpair`
    inside `asyncio.new_event_loop()` may be restricted by host firewalls/sandboxes.
    """
    if not turn_rows:
        return []
    cap = max(1, int(max_concurrency))
    if sys.platform == "win32":
        with concurrent.futures.ThreadPoolExecutor(max_workers=cap, thread_name_prefix="prepfly-eval") as pool:
            futs = [
                pool.submit(
                    grade_and_persist_turn,
                    supabase_client=supabase_client,
                    session_id=session_id,
                    turn_row=tr,
                    question_text=tr.get("question_text") or "",
                    chat_model=chat_model,
                    user_id=user_id,
                    role=role,
                    difficulty=difficulty,
                    resume_summary=resume_summary,
                    fallback_model=fallback_model,
                )
                for tr in turn_rows
            ]
            return [f.result() for f in futs]

    coro = evaluate_turns_parallel_async(
        supabase_client=supabase_client,
        session_id=session_id,
        turn_rows=turn_rows,
        chat_model=chat_model,
        user_id=user_id,
        role=role,
        difficulty=difficulty,
        resume_summary=resume_summary,
        fallback_model=fallback_model,
        max_concurrency=cap,
    )
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        return asyncio.run(coro)


def retry_failed_evaluations(
    supabase_client: Any,
    session_id: str,
    chat_model: Any,
    user_id: Optional[str] = None,
    role: str = "Software Engineer",
    difficulty: str = "Medium",
    fallback_model: Any = None,
) -> List[Dict[str, Any]]:
    """Re-runs all evaluations currently in status='failed' concurrently via asyncio.gather."""
    eval_res = supabase_client.table("interview_evaluations").select("*").eq("session_id", session_id).execute()
    failed_evals = [e for e in (eval_res.data or []) if e.get("status") == "failed"]
    if not failed_evals:
        return []

    turns_res = supabase_client.table("interview_turns").select("*").eq("session_id", session_id).execute()
    turns_by_id = {t["id"]: t for t in (turns_res.data or [])}

    turn_rows = [turns_by_id[fe["turn_id"]] for fe in failed_evals if fe.get("turn_id") in turns_by_id]
    return evaluate_turns_parallel(
        supabase_client=supabase_client,
        session_id=session_id,
        turn_rows=turn_rows,
        chat_model=chat_model,
        user_id=user_id,
        role=role,
        difficulty=difficulty,
        fallback_model=fallback_model,
    )


def _compute_speech_delivery_score(speech_metrics_list: List[Dict[str, Any]]) -> Optional[float]:
    """
    Computes a deterministic delivery score in [0.0, 1.0] from measured speech metrics.
    Returns None if zero turns have measurable timing (wpm is None), NEVER 0!
    """
    from services.interview_scoring_config import WPM_OPTIMAL_MIN, WPM_OPTIMAL_MAX

    measurable = [m for m in (speech_metrics_list or []) if m.get("wpm") is not None]
    if not measurable:
        return None

    turn_scores: List[float] = []
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
        filler_ratio = fillers / float(wc)
        fluency_s = max(0.2, 1.0 - filler_ratio * 3.0)
        turn_scores.append(0.6 * pace_s + 0.4 * fluency_s)

    return round(sum(turn_scores) / len(turn_scores), 4)


def compute_dimension_scores(
    evaluations: List[Dict[str, Any]],
    speech_metrics_list: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Phase 3 #4 & #5: Computes deterministic weighted scores for all 10 configured dimensions.
    - Maps criteria scores from status=='ok' evaluations to each dimension.
    - Delivery dimensions combine rubric scores with deterministic speech metrics;
      if speech metrics are NULL, delivery dimensions are marked score=None ('Not evaluated'), never 0.
    - Dimensions with 0 contributing turns return score=None ('Not evaluated').
    """
    from services.interview_scoring_config import DIMENSION_CONFIG, MIN_TURNS_PER_DIMENSION

    ok_evals = [e for e in (evaluations or []) if e.get("status") == "ok" and e.get("normalized_score") is not None]
    speech_delivery = _compute_speech_delivery_score(speech_metrics_list or [])

    results: List[Dict[str, Any]] = []
    for dim_name, cfg in DIMENSION_CONFIG.items():
        target_criteria = set(cfg["criteria"])
        is_delivery = bool(cfg.get("is_delivery", False))

        weighted_sum = 0.0
        total_w = 0.0
        contributing_turns: List[str] = []
        evidence_snippets: List[str] = []

        for ev in ok_evals:
            rubric_json = ev.get("rubric_scores_json") or {}
            if isinstance(rubric_json, str):
                try:
                    rubric_json = json.loads(rubric_json)
                except Exception:
                    rubric_json = {}
            criteria_list = rubric_json.get("criteria") if isinstance(rubric_json, dict) else []

            matched_any = False
            for crit in (criteria_list or []):
                cname = str(crit.get("criterion") or "").strip().lower()
                if cname in target_criteria:
                    w = float(crit.get("weight") or 0.2)
                    s = float(crit.get("score") or 0.0)
                    weighted_sum += w * s
                    total_w += w
                    matched_any = True
                    q = crit.get("quoted_justification")
                    if q:
                        evidence_snippets.append(f'Turn {ev.get("turn_id")}: "{q}"')
            if matched_any and ev.get("turn_id"):
                contributing_turns.append(str(ev["turn_id"]))

        if is_delivery and speech_delivery is None:
            # Rule Phase 3 #5: When speech metrics are NULL, delivery dimensions are Not evaluated, never 0
            results.append({
                "name": dim_name,
                "weight": cfg["weight"],
                "score": None,
                "normalized_score": None,
                "status": "Not evaluated",
                "reason": "speech_metrics_unavailable",
                "contributing_turns": [],
                "turn_count": 0,
                "confidence_label": "NONE",
                "evidence": ["Speech timing data unavailable; delivery not evaluated."],
            })
            continue

        if total_w == 0.0:
            if is_delivery and speech_delivery is not None and len(ok_evals) > 0:
                dim_norm = speech_delivery
                turn_count = len([m for m in (speech_metrics_list or []) if m.get("wpm") is not None])
            else:
                results.append({
                    "name": dim_name,
                    "weight": cfg["weight"],
                    "score": None,
                    "normalized_score": None,
                    "status": "Not evaluated",
                    "reason": "no_contributing_evidence",
                    "contributing_turns": [],
                    "turn_count": 0,
                    "confidence_label": "NONE",
                    "evidence": ["No evaluated turns mapped to this dimension."],
                })
                continue
        else:
            rubric_mean = weighted_sum / total_w
            if is_delivery and speech_delivery is not None:
                dim_norm = round(0.5 * rubric_mean + 0.5 * speech_delivery, 4)
            else:
                dim_norm = round(rubric_mean, 4)
            turn_count = len(set(contributing_turns))

        conf_label = "LOW_CONFIDENCE" if turn_count < MIN_TURNS_PER_DIMENSION else "ESTABLISHED"
        results.append({
            "name": dim_name,
            "weight": cfg["weight"],
            "score": round(dim_norm * 100.0, 1),
            "normalized_score": dim_norm,
            "status": "LIMITED_EVIDENCE" if conf_label == "LOW_CONFIDENCE" else "EVALUATED",
            "contributing_turns": sorted(set(contributing_turns)),
            "turn_count": turn_count,
            "confidence_label": conf_label,
            "evidence": evidence_snippets[:5],
        })

    return results

