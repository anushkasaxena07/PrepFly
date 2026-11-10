"""
Interview Capture Service (The Ground Truth Ledger)
Phase 2:
  - Immediately persists every interviewer question and candidate turn in `interview_turns`.
  - Records speech timing/engine/confidence and persists deterministic `interview_speech_metrics`.
  - Handles edge cases explicitly: typed vs speech, very short, "I don't know", off-topic,
    small talk, mic permission denied, STT low confidence, tab closed mid-interview.
  - Computes data sufficiency strictly from persisted turns.
  - Supports lossless page reload and non-repeating question stem checks.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.interview_scoring_config import (
    DONT_KNOW_PHRASES,
    MIN_WORDS_SUBSTANTIVE,
    SHORT_ANSWER_MAX_WORDS,
    SKIP_PHRASES,
    SMALL_TALK_PHRASES,
    STT_MIN_CONFIDENCE,
)
from services.interview_speech_service import (
    aggregate_session_speech_metrics,
    compute_speech_metrics,
    count_words,
)

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_stem(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", "", (text or "").lower())
    return " ".join(cleaned.split())


def is_duplicate_question_stem(candidate_id: Optional[str], new_question: str, current_questions: List[str], supabase_client: Any = None) -> bool:
    """Checks for repeated question stems across current session and past sessions of the same candidate."""
    new_norm = _normalize_stem(new_question)
    if not new_norm:
        return False

    seen_norms = {_normalize_stem(q) for q in (current_questions or []) if q}
    if new_norm in seen_norms:
        return True

    if supabase_client is not None and candidate_id:
        try:
            sess_res = supabase_client.table("sessions").select("session_id, questions").eq("user_id", str(candidate_id)).limit(20).execute()
            for row in (sess_res.data or []):
                qs = row.get("questions") or []
                if isinstance(qs, str):
                    try:
                        qs = json.loads(qs)
                    except Exception:
                        qs = []
                for q in qs:
                    if _normalize_stem(str(q)) == new_norm:
                        return True
        except Exception as e:
            logger.debug("Candidate history stem check skipped: %s", e)
    return False


def classify_turn_status(
    text: Optional[str],
    input_mode: str = "typed",
    stt_confidence: Optional[float] = None,
    edge_case: Optional[str] = None,
    confirmed_edit: bool = False,
    intent_hint: Optional[str] = None,
    is_small_talk_turn: bool = False,
) -> Tuple[str, str]:
    """
    Maps candidate utterance + capture telemetry into canonical Phase 2 turn status:
      ('answered' | 'skipped' | 'off_topic' | 'empty' | 'stt_failed' | 'stt_low_confidence' | 'small_talk', sub_reason)
    """
    edge = (edge_case or "").strip().lower()
    mode = (input_mode or "typed").strip().lower()
    raw = (text or "").strip()
    lowered = re.sub(r"[.!?,]+$", "", raw.lower()).strip()
    wc = count_words(raw)

    # 1. Hardware / STT failure edge cases
    if edge in ("mic_permission_denied", "stt_failed"):
        return "stt_failed", edge

    if edge == "tab_closed":
        return "skipped", "tab_closed"

    # 2. Spoken turn requiring user review BEFORE evaluation
    if mode == "speech" and not confirmed_edit:
        if not raw:
            return "stt_low_confidence", "empty_speech_transcript"
        if stt_confidence is not None and float(stt_confidence) < STT_MIN_CONFIDENCE:
            return "stt_low_confidence", "low_stt_confidence"

    # 3. Empty response (never evaluated as "bad answer")
    if not raw or wc == 0:
        return "empty", "empty_text"

    # 4. Interviewer-initiated small talk / conversational rapport
    if is_small_talk_turn or lowered in SMALL_TALK_PHRASES:
        return "small_talk", "rapport_or_greeting"

    # Check existing IntentClassifier if available
    if intent_hint:
        ih = intent_hint.upper()
        if ih in ("REPEAT", "REPEAT_REQUEST", "CLARIFY", "CLARIFICATION_REQUEST", "REPHRASE_REQUEST", "HINT_REQUEST", "PAUSE", "PAUSE_REQUEST", "RESUME_REQUEST", "SMALL_TALK"):
            return "small_talk", f"conversational_{ih.lower()}"
        if ih in ("NO_ANSWER", "SKIP_REQUEST"):
            if lowered in DONT_KNOW_PHRASES:
                return "skipped", "dont_know"
            return "skipped", "explicit_skip"
        if ih == "DONT_KNOW":
            return "skipped", "dont_know"
        if ih == "OFF_TOPIC":
            return "off_topic", "off_topic_utterance"
        if ih in ("EARLY_EXIT", "END_INTERVIEW_REQUEST"):
            return "skipped", "early_exit"

    # 5. Explicit skip or "I don't know"
    if lowered in SKIP_PHRASES:
        return "skipped", "explicit_skip"
    if lowered in DONT_KNOW_PHRASES or any(p in lowered for p in ("i don't know", "i dont know", "no idea")):
        # Note: still flagged cleanly with sub_reason="dont_know" for Phase 3/4 skill penalty without Strong Reject
        return "skipped", "dont_know"

    # 6. Off-topic / gibberish detection
    if re.fullmatch(r"([a-zA-Z])\1{3,}|test|asdf+|qwerty+|1234+", lowered):
        return "off_topic", "gibberish_or_spam"

    # Off-topic explicit conversational derailments unrelated to any prompt
    off_topic_markers = ("what is the weather", "tell me a joke", "order pizza", "play music", "who won the match")
    if any(m in lowered for m in off_topic_markers):
        return "off_topic", "off_topic_utterance"

    # 7. Substantive vs very short answer
    if wc < MIN_WORDS_SUBSTANTIVE:
        return "answered", "very_short"

    return "answered", "substantive"


def persist_interviewer_turn(
    supabase_client: Any,
    session_id: str,
    turn_index: int,
    question_text: str,
    question_id: Optional[str] = None,
    skill_id: Optional[str] = None,
    stage: Optional[str] = None,
    question_type: Optional[str] = None,
    started_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Immediately persists an interviewer question turn into `interview_turns`."""
    now_iso = started_at or _utc_now_iso()
    turn_id = f"turn_{session_id}_{turn_index}_interviewer"
    row = {
        "id": turn_id,
        "session_id": session_id,
        "turn_number": turn_index + 1,
        "turn_index": int(turn_index),
        "speaker": "interviewer",
        "question_id": question_id or f"q_{session_id[:8]}_{turn_index}",
        "skill_id": skill_id,
        "question_text": question_text,
        "text": question_text,
        "question_type": question_type or "technical",
        "stage": stage or "Technical",
        "word_count": count_words(question_text),
        "started_at": now_iso,
        "ended_at": now_iso,
        "turn_status": "small_talk" if (stage or "").lower() == "small_talk" else "answered",
        "created_at": now_iso,
    }
    supabase_client.table("interview_turns").upsert(row, on_conflict="id").execute()
    return row


def persist_candidate_turn(
    supabase_client: Any,
    session_id: str,
    turn_index: int,
    text: Optional[str],
    question_text: Optional[str] = None,
    question_id: Optional[str] = None,
    skill_id: Optional[str] = None,
    stage: Optional[str] = None,
    input_mode: str = "typed",
    stt_engine: Optional[str] = None,
    stt_confidence: Optional[float] = None,
    audio_ref: Optional[str] = None,
    audio_duration_s: Optional[float] = None,
    started_at: Optional[str] = None,
    ended_at: Optional[str] = None,
    word_timestamps: Optional[List[Dict[str, Any]]] = None,
    edge_case: Optional[str] = None,
    confirmed_edit: bool = False,
    intent_hint: Optional[str] = None,
    is_small_talk_turn: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Immediately persists a candidate turn into `interview_turns` AND its deterministic speech
    telemetry row into `interview_speech_metrics`. Fails loudly on DB error (never swallowed).
    Returns (turn_row, speech_metrics_row).
    """
    now_iso = _utc_now_iso()
    clean_text = (text or "").strip()
    mode = (input_mode or "typed").strip().lower()
    if mode not in ("typed", "speech"):
        mode = "typed"

    turn_status, sub_reason = classify_turn_status(
        text=clean_text,
        input_mode=mode,
        stt_confidence=stt_confidence,
        edge_case=edge_case,
        confirmed_edit=confirmed_edit,
        intent_hint=intent_hint,
        is_small_talk_turn=is_small_talk_turn,
    )

    wc = count_words(clean_text)
    turn_id = f"turn_{session_id}_{turn_index}_candidate"
    turn_row = {
        "id": turn_id,
        "session_id": session_id,
        "turn_number": turn_index + 1,
        "turn_index": int(turn_index),
        "speaker": "candidate",
        "question_id": question_id,
        "skill_id": skill_id,
        "question_text": question_text or "",
        "text": clean_text,
        "stage": stage,
        "candidate_response": clean_text,
        "input_mode": mode,
        "stt_engine": stt_engine if mode == "speech" else None,
        "stt_confidence": float(stt_confidence) if (mode == "speech" and stt_confidence is not None) else None,
        "audio_ref": audio_ref,
        "audio_duration_s": float(audio_duration_s) if audio_duration_s is not None else None,
        "started_at": started_at or now_iso,
        "ended_at": ended_at or now_iso,
        "word_count": wc,
        "turn_status": turn_status,
        "intent": intent_hint or sub_reason,
        "created_at": now_iso,
    }

    supabase_client.table("interview_turns").upsert(turn_row, on_conflict="id").execute()

    speech_metrics = compute_speech_metrics(
        text=clean_text,
        input_mode=mode,
        audio_duration_s=audio_duration_s,
        started_at=started_at,
        ended_at=ended_at,
        word_timestamps=word_timestamps,
    )
    speech_row = {
        "turn_id": turn_id,
        "session_id": session_id,
        "wpm": speech_metrics["wpm"],
        "filler_count": speech_metrics["filler_count"],
        "filler_map_json": speech_metrics["filler_map_json"],
        "pause_count": speech_metrics["pause_count"],
        "longest_pause_s": speech_metrics["longest_pause_s"],
        "avg_pause_s": speech_metrics["avg_pause_s"],
        "speaking_time_s": speech_metrics["speaking_time_s"],
        "silence_ratio": speech_metrics["silence_ratio"],
        "computed_by": speech_metrics["computed_by"],
        "formula_version": speech_metrics["formula_version"],
        "missing_reason": speech_metrics["missing_reason"],
        "created_at": now_iso,
    }
    supabase_client.table("interview_speech_metrics").upsert(speech_row, on_conflict="turn_id").execute()
    return turn_row, speech_row


def get_session_turns_and_metrics(supabase_client: Any, session_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Reads all persisted turns & speech metrics for a session sorted deterministically by (turn_index, speaker)."""
    turns_res = supabase_client.table("interview_turns").select("*").eq("session_id", session_id).execute()
    turns = list(turns_res.data or []) if turns_res else []
    turns.sort(key=lambda r: (int(r.get("turn_index") if r.get("turn_index") is not None else (r.get("turn_number") or 0)), 0 if r.get("speaker") == "interviewer" else 1))

    metrics_res = supabase_client.table("interview_speech_metrics").select("*").eq("session_id", session_id).execute()
    metrics = list(metrics_res.data or []) if metrics_res else []
    return turns, metrics


def compute_data_sufficiency(supabase_client: Any, session_id: str) -> Dict[str, Any]:
    """
    Computes data sufficiency strictly from persisted `interview_turns` and `interview_speech_metrics`:
      - answered_substantive_turns (>= MIN_WORDS_SUBSTANTIVE & status == 'answered')
      - skills_touched
      - total_speaking_time_s (None if no speech duration was recorded)
      - total_words & turn counts by status
    """
    turns, metrics = get_session_turns_and_metrics(supabase_client, session_id)
    candidate_turns = [t for t in turns if t.get("speaker") == "candidate"]

    answered_substantive = 0
    total_words = 0
    skills_touched: List[str] = []
    status_counts: Dict[str, int] = {
        "answered": 0,
        "skipped": 0,
        "off_topic": 0,
        "empty": 0,
        "stt_failed": 0,
        "stt_low_confidence": 0,
        "small_talk": 0,
    }

    for t in candidate_turns:
        st = t.get("turn_status") or "answered"
        status_counts[st] = status_counts.get(st, 0) + 1
        wc = int(t.get("word_count") or count_words(t.get("text") or ""))

        if st != "small_talk":
            total_words += wc
            if t.get("skill_id") and st in ("answered", "skipped") and t.get("skill_id") not in skills_touched:
                skills_touched.append(str(t["skill_id"]))
        if st == "answered" and wc >= MIN_WORDS_SUBSTANTIVE:
            answered_substantive += 1

    non_small_talk_turn_ids = {
        t.get("id") for t in candidate_turns if (t.get("turn_status") or "answered") != "small_talk"
    }
    interview_metrics = [m for m in metrics if m.get("turn_id") in non_small_talk_turn_ids]
    speech_agg = aggregate_session_speech_metrics(interview_metrics)

    return {
        "total_candidate_turns": len([t for t in candidate_turns if (t.get("turn_status") or "") != "small_talk"]),
        "answered_substantive_turns": answered_substantive,
        "total_words": total_words,
        "skills_touched": sorted(skills_touched),
        "total_speaking_time_s": speech_agg["speaking_time_s"],
        "measurable_speech_turns": speech_agg["measurable_turns"],
        "status_counts": status_counts,
        "speech_summary": speech_agg,
    }


def get_persisted_interview_state(supabase_client: Any, session_id: str) -> Dict[str, Any]:
    """Reconstructs complete interview state from DB for page refresh / session resume."""
    sess_res = supabase_client.table("sessions").select("*").eq("session_id", session_id).limit(1).execute()
    session_row = sess_res.data[0] if (sess_res and sess_res.data) else None
    if not session_row:
        return {}

    turns, metrics = get_session_turns_and_metrics(supabase_client, session_id)
    metrics_by_turn = {m.get("turn_id"): m for m in metrics}
    for t in turns:
        tid = t.get("id")
        if tid in metrics_by_turn:
            t["speech_metrics"] = metrics_by_turn[tid]

    sufficiency = compute_data_sufficiency(supabase_client, session_id)
    last_interviewer = next((t for t in reversed(turns) if t.get("speaker") == "interviewer"), None)

    return {
        "session_id": session_id,
        "status": session_row.get("status") or ("completed" if session_row.get("active") in (False, 0) else "in_progress"),
        "display_name": session_row.get("display_name") or "Candidate",
        "display_name_source": session_row.get("display_name_source") or "fallback",
        "role": session_row.get("role") or "Software Engineer",
        "category": session_row.get("category") or "Core CS",
        "difficulty": session_row.get("difficulty") or "Medium",
        "question_index": session_row.get("question_index") or 1,
        "current_question": (last_interviewer or {}).get("text") or ((session_row.get("questions") or [None])[-1] if isinstance(session_row.get("questions"), list) and session_row.get("questions") else None),
        "turns": turns,
        "data_sufficiency": sufficiency,
    }
