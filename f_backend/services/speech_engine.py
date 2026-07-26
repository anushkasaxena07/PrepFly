"""
speech_engine.py — Deterministic Speech Analysis Engine for PrepFly.

Computes exact speech metrics without relying on LLM guesses:
 1. WPM (Words Per Minute) = total_words / (duration_seconds / 60)
 2. Filler words detection via word-boundary regex (um, uh, like, so, basically, etc.)
 3. Pauses detection (gaps between timestamps > 500ms, or punctuation-based fallback)
 4. Pace consistency (rolling 10s WPM variance)
 5. Vocabulary diversity & word repetition frequency
 6. Weighted overall score (0.0 to 10.0) & tone indicators
 7. AI narrative layer fed REAL computed data (with deterministic fallback)
"""

import re
import math
from typing import List, Dict, Any, Optional

# ── Filler word dictionary ────────────────────────────────────────────────────
FILLER_WORDS = [
    'um', 'uh', 'er', 'ah', 'like', 'so', 'actually', 'basically',
    'you know', 'i mean', 'sort of', 'kind of', 'literally', 'honestly',
    'anyway', 'right', 'obviously', 'seriously', 'at the end of the day'
]

# Stop words for vocabulary repetition check
STOP_WORDS = set([
    'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'to', 'from',
    'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then',
    'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any',
    'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
    'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's',
    't', 'can', 'will', 'just', 'don', 'should', 'now', 'i', 'you', 'he',
    'she', 'it', 'we', 'they', 'my', 'your', 'his', 'her', 'its', 'our',
    'their', 'that', 'this', 'these', 'those', 'with', 'for', 'about', 'as'
])


def extract_fillers(text: str) -> Dict[str, Any]:
    """Find all filler words in text using word-boundary regex."""
    text_lower = text.lower()
    found_counts = {}
    total_fillers = 0

    # Sort fillers by length descending to match multi-word phrases first ('you know' before 'so')
    sorted_fillers = sorted(FILLER_WORDS, key=len, reverse=True)

    remaining_text = text_lower
    for filler in sorted_fillers:
        escaped = re.escape(filler)
        pattern = rf'\b{escaped}\b'
        matches = re.findall(pattern, remaining_text)
        count = len(matches)
        if count > 0:
            found_counts[filler] = count
            total_fillers += count
            # Remove matched filler phrase to avoid double-counting
            remaining_text = re.sub(pattern, ' ', remaining_text)

    return {
        "filler_count": total_fillers,
        "filler_breakdown": found_counts,
        "fillers_found": list(found_counts.keys())
    }


def detect_pauses(words_data: List[Dict[str, Any]], threshold_ms: int = 500) -> List[Dict[str, Any]]:
    """
    Detect pauses from word-level timestamp array: [{text: "hello", start: 0, end: 350}, ...]
    A gap between word[i].end and word[i+1].start > threshold_ms is flagged as a pause.
    """
    pauses = []
    if not words_data or len(words_data) < 2:
        return pauses

    for i in range(len(words_data) - 1):
        curr_end = words_data[i].get("end") or 0
        next_start = words_data[i + 1].get("start") or 0
        gap = next_start - curr_end
        if gap > threshold_ms:
            pauses.append({
                "after_word": words_data[i].get("text", ""),
                "duration_ms": gap,
                "duration_sec": round(gap / 1000.0, 2),
                "position": i
            })

    return pauses


def calculate_pace_consistency(words_data: List[Dict[str, Any]], window_sec: float = 10.0) -> Dict[str, Any]:
    """Calculate rolling WPM in window_sec windows to evaluate pace stability."""
    if not words_data or len(words_data) < 5:
        return {"consistent": True, "std_dev": 0.0, "windows_wpm": []}

    window_ms = window_sec * 1000.0
    total_duration_ms = words_data[-1].get("end", 0) - words_data[0].get("start", 0)

    if total_duration_ms < window_ms:
        return {"consistent": True, "std_dev": 0.0, "windows_wpm": []}

    num_windows = math.ceil(total_duration_ms / window_ms)
    window_counts = [0] * num_windows

    start_time = words_data[0].get("start", 0)
    for w in words_data:
        w_start = w.get("start", 0) - start_time
        idx = min(int(w_start // window_ms), num_windows - 1)
        window_counts[idx] += 1

    # Convert window counts to WPM (count * (60 / window_sec))
    windows_wpm = [round(c * (60.0 / window_sec)) for c in window_counts if c > 0]

    if not windows_wpm:
        return {"consistent": True, "std_dev": 0.0, "windows_wpm": []}

    avg_wpm = sum(windows_wpm) / len(windows_wpm)
    variance = sum((w - avg_wpm) ** 2 for w in windows_wpm) / len(windows_wpm)
    std_dev = math.sqrt(variance)

    # Pace is consistent if standard deviation is less than 30% of average WPM
    is_consistent = std_dev < (avg_wpm * 0.3)

    return {
        "consistent": is_consistent,
        "avg_window_wpm": round(avg_wpm),
        "std_dev": round(std_dev, 1),
        "windows_wpm": windows_wpm
    }


def analyze_vocabulary(text: str) -> Dict[str, Any]:
    """Extract vocabulary metrics: unique word count, diversity ratio, and overused words."""
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
    total_count = len(words)
    if total_count == 0:
        return {"total_words": 0, "unique_words": 0, "diversity_pct": 0, "overused_words": []}

    unique_words = set(words)
    diversity_pct = round((len(unique_words) / total_count) * 100)

    # Word frequency analysis (exclude stop words)
    freq = {}
    for w in words:
        if w not in STOP_WORDS and w not in FILLER_WORDS:
            freq[w] = freq.get(w, 0) + 1

    overused = [{ "word": w, "count": c } for w, c in freq.items() if c >= 4]
    overused.sort(key=lambda x: x["count"], reverse=True)

    return {
        "total_words": total_count,
        "unique_words": len(unique_words),
        "diversity_pct": diversity_pct,
        "overused_words": overused[:5]
    }


def compute_speech_metrics(
    transcript: str,
    duration_seconds: float = 60.0,
    words_data: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Main deterministic speech metrics calculator.
    Returns exact numbers for WPM, fillers, pauses, vocabulary, tone, and overall score.
    """
    cleaned_transcript = transcript.strip()
    words = re.findall(r'\b\w+\b', cleaned_transcript)
    total_words = len(words)

    # Duration fallback (avoid divide by zero)
    duration_seconds = max(5.0, float(duration_seconds or 60.0))
    duration_minutes = duration_seconds / 60.0

    # 1. WPM
    wpm = round(total_words / duration_minutes)

    # 2. Fillers
    filler_res = extract_fillers(cleaned_transcript)
    filler_count = filler_res["filler_count"]
    fillers_per_min = round(filler_count / duration_minutes, 1)

    # 3. Pauses & Pace
    if words_data:
        pauses = detect_pauses(words_data, threshold_ms=500)
        pace_info = calculate_pace_consistency(words_data)
    else:
        # Punctuation-based pause approximation when raw timestamps aren't present
        pause_symbols = re.findall(r'(\.\.\.|\-\-|[,\.\?!])', cleaned_transcript)
        pauses = [{"duration_ms": 600} for _ in pause_symbols if _ in ['...', '--', '.']]
        pace_info = {"consistent": True, "std_dev": 0.0, "windows_wpm": []}

    pause_count = len(pauses)
    longest_pause_ms = max([p.get("duration_ms", 0) for p in pauses], default=0)

    # 4. Vocabulary
    vocab_info = analyze_vocabulary(cleaned_transcript)

    # 5. Deterministic Sub-scores (0-100)
    # WPM score: ideal speed 130-160 WPM
    if 125 <= wpm <= 165:
        wpm_score = 95
    elif 100 <= wpm < 125:
        wpm_score = 80 + int((wpm - 100) * 0.6)
    elif 165 < wpm <= 190:
        wpm_score = 95 - int((wpm - 165) * 0.8)
    elif wpm < 100:
        wpm_score = max(30, 50 + int(wpm * 0.3))
    else:
        wpm_score = max(30, 70 - int((wpm - 190) * 0.5))

    # Filler score: 0 fillers = 100, 10+ fillers per min = 30
    filler_score = max(20, round(100 - (fillers_per_min * 12)))

    # Vocabulary score: diversity ratio (target ~55%+)
    vocab_score = min(100, max(40, round(vocab_info["diversity_pct"] * 1.5)))

    # Pace score
    pace_score = 90 if pace_info["consistent"] else 65

    # 6. Overall Confidence & Score (0.0 - 10.0 scale)
    confidence_pct = round(
        wpm_score * 0.30 +
        filler_score * 0.30 +
        vocab_score * 0.20 +
        pace_score * 0.20
    )

    overall_score = round(max(1.0, min(10.0, confidence_pct / 10.0)), 1)

    # Tone indicators derived from objective data
    tone = {
        "confidence": max(30, min(99, confidence_pct)),
        "clarity": max(30, min(99, round(filler_score * 0.6 + wpm_score * 0.4))),
        "enthusiasm": max(40, min(95, round(wpm_score * 0.5 + vocab_score * 0.5))),
        "nervousness": max(5, min(90, round((fillers_per_min * 10) + (100 - pace_score) * 0.5)))
    }

    return {
        "confidence_pct": confidence_pct,
        "wpm": wpm,
        "filler_count": filler_count,
        "fillers_per_min": fillers_per_min,
        "filler_breakdown": filler_res["filler_breakdown"],
        "fillers_found": filler_res["fillers_found"],
        "pause_count": pause_count,
        "longest_pause_ms": longest_pause_ms,
        "pace_consistent": pace_info["consistent"],
        "vocabulary_diversity": vocab_info["diversity_pct"],
        "total_words": total_words,
        "overused_words": vocab_info["overused_words"],
        "overall_score": overall_score,
        "sub_scores": {
            "wpm": wpm_score,
            "fillers": filler_score,
            "vocabulary": vocab_score,
            "pace": pace_score
        },
        "tone": tone
    }


def generate_speech_feedback(metrics: Dict[str, Any], chat_model=None) -> List[str]:
    """
    Generate feedback starting from real calculated metrics.
    Uses LLM for natural narrative if available, otherwise generates structured emoji feedback.
    """
    if chat_model:
        try:
            from langchain_core.messages import HumanMessage
            import json

            prompt = f"""You are an expert public speaking & communications coach.
Below are exact MEASURED speech metrics calculated from a candidate's response (do NOT invent new metrics):

- Speaking Speed: {metrics['wpm']} WPM
- Filler Words: {metrics['filler_count']} total ({metrics['fillers_per_min']} / min). Breakdown: {json.dumps(metrics['filler_breakdown'])}
- Pauses: {metrics['pause_count']} detected, longest: {metrics['longest_pause_ms']}ms
- Pace Consistency: {'Consistent & Steady' if metrics['pace_consistent'] else 'Inconsistent / Unsteady'}
- Vocabulary Diversity: {metrics['vocabulary_diversity']}% unique words
- Overall Score: {metrics['overall_score']}/10

Write 4-5 concise, professional feedback points starting with emojis:
- Start with a positive strength (✅)
- Mention filler word observations (⚠️)
- Note pace and speaking speed (📈)
- Provide an actionable improvement tip (💡)

Return ONLY a JSON array of strings, e.g. ["✅ ...", "⚠️ ...", "📈 ...", "💡 ..."]. No markdown wrappers."""

            res_raw = chat_model.invoke([HumanMessage(content=prompt)]).content.strip()
            # Clean markdown code blocks
            if res_raw.startswith("```"):
                res_raw = re.sub(r"^```[a-z]*\n", "", res_raw)
                res_raw = re.sub(r"\n```$", "", res_raw)

            parsed = json.loads(res_raw)
            if isinstance(parsed, list) and len(parsed) >= 3:
                return parsed
        except Exception as e:
            print(f"LLM speech feedback notice (using deterministic fallback): {e}")

    # Deterministic fallback feedback
    feedback = []

    # Strength
    if metrics["wpm"] >= 120 and metrics["wpm"] <= 165:
        feedback.append(f"✅ Ideal speaking pace at {metrics['wpm']} WPM — clear and easy for interviewers to follow.")
    elif metrics["vocabulary_diversity"] >= 50:
        feedback.append(f"✅ Strong vocabulary range with {metrics['vocabulary_diversity']}% unique word usage.")
    else:
        feedback.append(f"✅ Clear articulation with {metrics['total_words']} words delivered in your response.")

    # Fillers
    if metrics["filler_count"] == 0:
        feedback.append("✅ Excellent delivery with 0 filler words detected!")
    elif metrics["filler_count"] <= 3:
        fillers_str = ", ".join([f"'{w}' ({c}x)" for w, c in metrics["filler_breakdown"].items()])
        feedback.append(f"⚠️ Low filler usage ({metrics['filler_count']} total: {fillers_str}). Minor adjustment needed.")
    else:
        fillers_str = ", ".join([f"'{w}' ({c}x)" for w, c in metrics["filler_breakdown"].items()])
        feedback.append(f"⚠️ High filler count ({metrics['filler_count']} fillers: {fillers_str}). Practice replacing fillers with deliberate pauses.")

    # Pace & Pauses
    if metrics["wpm"] < 110:
        feedback.append(f"📈 Speaking speed is slightly slow ({metrics['wpm']} WPM). Aim for 130–150 WPM for maximum engagement.")
    elif metrics["wpm"] > 170:
        feedback.append(f"📈 Speaking speed is fast ({metrics['wpm']} WPM). Slow down slightly to give interviewers time to digest key points.")
    else:
        feedback.append(f"📈 Pace is consistent across your response at {metrics['wpm']} WPM.")

    # Actionable Tip
    if metrics["overused_words"]:
        top_word = metrics["overused_words"][0]["word"]
        feedback.append(f"💡 Tip: You repeated '{top_word}' {metrics['overused_words'][0]['count']} times. Try using synonyms like '{top_word} alternative'.")
    else:
        feedback.append("💡 Tip: Take a brief 1-second pause before answering complex questions to structure your thoughts clearly.")

    return feedback
