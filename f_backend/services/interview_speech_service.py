"""
Deterministic Speech Telemetry Service (Pure Python, Unit-Tested)
Operating Rules R1, R3:
  - WPM = word_count / speaking_time_minutes
  - Filler word detection from centralized FILLER_WORDS
  - Pause detection from word timestamps when available, else NULL ("not measurable")
  - Speaking vs silence ratio
  - Missing timing data -> NULL (None) with explicit missing_reason, NEVER 0.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from services.interview_scoring_config import (
    FILLER_WORDS,
    FORMULA_VERSION,
    MIN_SPEECH_DURATION_S,
    PAUSE_GAP_THRESHOLD_S,
)


def count_words(text: Optional[str]) -> int:
    if not text or not isinstance(text, str):
        return 0
    return len(re.findall(r"\b[\w']+\b", text.strip()))


def _parse_iso_seconds(started_at: Optional[str], ended_at: Optional[str]) -> Optional[float]:
    if not started_at or not ended_at:
        return None
    try:
        s_str = str(started_at).strip().replace("Z", "+00:00")
        e_str = str(ended_at).strip().replace("Z", "+00:00")
        dt_s = datetime.fromisoformat(s_str)
        dt_e = datetime.fromisoformat(e_str)
        diff = (dt_e - dt_s).total_seconds()
        return diff if diff > 0 else None
    except Exception:
        return None


def detect_fillers(text: Optional[str], filler_list: Optional[List[str]] = None) -> Dict[str, int]:
    if not text or not isinstance(text, str):
        return {}
    lowered = text.lower()
    targets = filler_list if filler_list is not None else FILLER_WORDS
    counts: Dict[str, int] = {}
    for phrase in targets:
        matches = len(re.findall(r"\b" + re.escape(phrase.lower()) + r"\b", lowered))
        if matches > 0:
            counts[phrase] = matches
    return counts


def compute_speech_metrics(
    text: Optional[str],
    input_mode: str = "speech",
    audio_duration_s: Optional[float] = None,
    started_at: Optional[str] = None,
    ended_at: Optional[str] = None,
    word_timestamps: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Computes deterministic speech metrics for a candidate turn.
    Any unavailable metric is strictly returned as None (SQL NULL), never coerced to 0.
    """
    mode = (input_mode or "speech").strip().lower()
    wc = count_words(text)

    base = {
        "word_count": wc,
        "wpm": None,
        "filler_count": None,
        "filler_map_json": {},
        "pause_count": None,
        "longest_pause_s": None,
        "avg_pause_s": None,
        "speaking_time_s": None,
        "silence_ratio": None,
        "pauses_status": "not_measurable",
        "computed_by": "deterministic_python",
        "formula_version": FORMULA_VERSION,
        "missing_reason": None,
    }

    if mode == "typed":
        base["missing_reason"] = "typed_input_not_applicable"
        base["pauses_status"] = "not_applicable"
        return base

    if wc == 0:
        base["missing_reason"] = "empty_transcript"
        base["pauses_status"] = "not_measurable"
        return base

    # Resolve speaking duration in seconds
    duration_s: Optional[float] = None
    if audio_duration_s is not None:
        try:
            val = float(audio_duration_s)
            if val >= MIN_SPEECH_DURATION_S:
                duration_s = val
        except (TypeError, ValueError):
            duration_s = None

    if duration_s is None:
        iso_diff = _parse_iso_seconds(started_at, ended_at)
        if iso_diff is not None and iso_diff >= MIN_SPEECH_DURATION_S:
            duration_s = iso_diff

    if duration_s is None:
        base["missing_reason"] = "timing_data_unavailable"
        base["pauses_status"] = "not_measurable"
        return base

    # Duration is available -> compute deterministic WPM & filler metrics
    speaking_minutes = duration_s / 60.0
    wpm = round(wc / speaking_minutes, 1)
    filler_map = detect_fillers(text)
    filler_total = sum(filler_map.values())

    base["wpm"] = wpm
    base["speaking_time_s"] = round(duration_s, 3)
    base["filler_count"] = filler_total
    base["filler_map_json"] = filler_map

    # Pause & silence ratio computation from word timestamps when available
    valid_ts = [
        w for w in (word_timestamps or [])
        if isinstance(w, dict) and isinstance(w.get("start"), (int, float)) and isinstance(w.get("end"), (int, float))
    ]
    if len(valid_ts) >= 2:
        sorted_ts = sorted(valid_ts, key=lambda x: x["start"])
        pauses: List[float] = []
        active_speech_s = 0.0
        for idx, item in enumerate(sorted_ts):
            w_dur = max(0.0, float(item["end"]) - float(item["start"]))
            active_speech_s += w_dur
            if idx > 0:
                gap = float(item["start"]) - float(sorted_ts[idx - 1]["end"])
                if gap >= PAUSE_GAP_THRESHOLD_S:
                    pauses.append(gap)

        base["pause_count"] = len(pauses)
        base["longest_pause_s"] = round(max(pauses), 3) if pauses else 0.0
        base["avg_pause_s"] = round(sum(pauses) / len(pauses), 3) if pauses else 0.0
        base["silence_ratio"] = round(max(0.0, min(1.0, (duration_s - active_speech_s) / duration_s)), 3)
        base["pauses_status"] = "measured"
        base["missing_reason"] = None
    else:
        base["pauses_status"] = "not_measurable"
        base["missing_reason"] = "word_timestamps_unavailable"

    return base


def aggregate_session_speech_metrics(metrics_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregates persisted `interview_speech_metrics` across candidate turns.
    Never converts missing metrics into 0: returns None if zero turns are measurable.
    """
    measurable_wpm = [
        (m["wpm"], m.get("speaking_time_s") or 0.0)
        for m in metrics_rows
        if m.get("wpm") is not None and (m.get("speaking_time_s") or 0.0) > 0
    ]
    total_speaking_s = sum(dur for _, dur in measurable_wpm) if measurable_wpm else None
    if measurable_wpm and total_speaking_s and total_speaking_s > 0:
        # Duration-weighted WPM across measurable turns
        weighted_wpm = round(sum(w * dur for w, dur in measurable_wpm) / total_speaking_s, 1)
    else:
        weighted_wpm = None

    measurable_fillers = [m for m in metrics_rows if m.get("filler_count") is not None]
    if measurable_fillers:
        total_fillers = sum(int(m["filler_count"]) for m in measurable_fillers)
        merged_map: Dict[str, int] = {}
        for m in measurable_fillers:
            fmap = m.get("filler_map_json") or {}
            if isinstance(fmap, dict):
                for k, v in fmap.items():
                    merged_map[k] = merged_map.get(k, 0) + int(v)
    else:
        total_fillers = None
        merged_map = {}

    measurable_pauses = [m for m in metrics_rows if m.get("pause_count") is not None]
    if measurable_pauses:
        total_pauses = sum(int(m["pause_count"]) for m in measurable_pauses)
        longest_pause = max(float(m.get("longest_pause_s") or 0.0) for m in measurable_pauses)
        avg_pause = round(sum(float(m.get("avg_pause_s") or 0.0) for m in measurable_pauses) / len(measurable_pauses), 3)
        pauses_status = "measured"
    else:
        total_pauses = None
        longest_pause = None
        avg_pause = None
        pauses_status = "not_measurable"

    measurable_sil = [m["silence_ratio"] for m in metrics_rows if m.get("silence_ratio") is not None]
    avg_silence = round(sum(float(s) for s in measurable_sil) / len(measurable_sil), 3) if measurable_sil else None

    return {
        "wpm": weighted_wpm,
        "filler_count": total_fillers,
        "filler_breakdown": merged_map,
        "pause_count": total_pauses,
        "longest_pause_s": longest_pause,
        "avg_pause_s": avg_pause,
        "speaking_time_s": round(total_speaking_s, 3) if total_speaking_s is not None else None,
        "silence_ratio": avg_silence,
        "pauses_status": pauses_status,
        "measurable_turns": len(measurable_wpm),
        "formula_version": FORMULA_VERSION,
    }

