import re

FILLER_WORDS = ["um", "uh", "like", "basically", "you know", "actually", "literally", "sort of", "kind of"]

def analyze_live_response(answer_text, duration_seconds=15):
    if not answer_text or not answer_text.strip():
        return {
            "wpm": 0,
            "filler_words_count": 0,
            "filler_words_detected": [],
            "communication_rating": "Fair",
            "confidence_score": 5.0,
            "technical_accuracy": 5.0,
            "word_count": 0,
            "pause_frequency": "Normal"
        }

    words = re.findall(r'\b\w+\b', answer_text.lower())
    word_count = len(words)
    
    # Words per minute calculation
    wpm = int((word_count / max(duration_seconds, 5)) * 60) if duration_seconds > 0 else int(word_count * 4)
    wpm = min(max(wpm, 40), 220)

    # Filler words detection
    found_fillers = []
    for fw in FILLER_WORDS:
        matches = len(re.findall(r'\b' + re.escape(fw) + r'\b', answer_text.lower()))
        if matches > 0:
            found_fillers.append(f"{fw} ({matches})")
    
    total_fillers = sum([len(re.findall(r'\b' + re.escape(fw) + r'\b', answer_text.lower())) for fw in FILLER_WORDS])

    # Confidence calculation
    confidence = 8.5
    if total_fillers > 3: confidence -= 1.5
    if word_count < 15: confidence -= 2.0
    elif word_count > 60: confidence += 0.5
    confidence = round(min(max(confidence, 4.0), 9.8), 1)

    # Communication rating
    if confidence >= 8.5 and total_fillers <= 1:
        comm_rating = "Excellent"
    elif confidence >= 7.0 and total_fillers <= 3:
        comm_rating = "Good"
    elif confidence >= 5.5:
        comm_rating = "Average"
    else:
        comm_rating = "Needs Improvement"

    return {
        "wpm": wpm,
        "filler_words_count": total_fillers,
        "filler_words_detected": found_fillers,
        "communication_rating": comm_rating,
        "confidence_score": confidence,
        "word_count": word_count,
        "pause_frequency": "High" if total_fillers >= 4 else "Optimal"
    }
