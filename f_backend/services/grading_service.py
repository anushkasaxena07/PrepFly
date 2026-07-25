# Professional Grading System Service
import math

GRADE_TIERS = [
    {"min": 95, "grade": "A+", "label": "Outstanding", "desc": "Ready for Senior Engineering Role", "color": "#059669", "bgColor": "rgba(5, 150, 105, 0.15)", "rec": "Strong Hire", "level": "Elite"},
    {"min": 90, "grade": "A", "label": "Excellent", "desc": "Strong Technical & Problem Solving Skills", "color": "#22c55e", "bgColor": "rgba(34, 197, 94, 0.15)", "rec": "Hire", "level": "Excellent"},
    {"min": 85, "grade": "A-", "label": "Very Good", "desc": "Demonstrates Solid Core Competency", "color": "#4ade80", "bgColor": "rgba(74, 222, 128, 0.15)", "rec": "Hire with Reservations", "level": "Good"},
    {"min": 80, "grade": "B+", "label": "Good", "desc": "Minor Improvements Required in Depth", "color": "#2563eb", "bgColor": "rgba(37, 99, 235, 0.15)", "rec": "Hire with Reservations", "level": "Good"},
    {"min": 75, "grade": "B", "label": "Above Average", "desc": "Moderate Knowledge Gaps Identified", "color": "#38bdf8", "bgColor": "rgba(56, 189, 248, 0.15)", "rec": "Borderline", "level": "Average"},
    {"min": 70, "grade": "B-", "label": "Average", "desc": "Incomplete Explanations & Superficial Depth", "color": "#14b8a6", "bgColor": "rgba(20, 184, 166, 0.15)", "rec": "Borderline", "level": "Average"},
    {"min": 65, "grade": "C+", "label": "Fair", "desc": "Substantial Mistakes & Lack of Trade-off Analysis", "color": "#f97316", "bgColor": "rgba(249, 115, 22, 0.15)", "rec": "No Hire", "level": "Below Average"},
    {"min": 60, "grade": "C", "label": "Needs Improvement", "desc": "Failed Technical Criteria & Missing Edge Cases", "color": "#f59e0b", "bgColor": "rgba(245, 158, 11, 0.15)", "rec": "No Hire", "level": "Below Average"},
    {"min": 50, "grade": "D", "label": "Poor Performance", "desc": "Major Conceptual Mistakes & Poor Structure", "color": "#ef4444", "bgColor": "rgba(239, 68, 68, 0.15)", "rec": "Strong No Hire", "level": "Beginner"},
    {"min": 0,  "grade": "F", "label": "Significant Improvement Required", "desc": "Completely Wrong or No Answer Provided", "color": "#991b1b", "bgColor": "rgba(153, 27, 27, 0.15)", "rec": "Strong No Hire", "level": "Beginner"}
]

def calculate_grade_info(score_100: float) -> dict:
    s = min(100.0, max(0.0, round(float(score_100))))
    for tier in GRADE_TIERS:
        if s >= tier["min"]:
            res = dict(tier)
            res["score"] = int(s)
            return res
    return dict(GRADE_TIERS[-1])


def compute_section_grades(feedbacks: list, raw_metrics: dict = None) -> list:
    """
    Computes deterministic scores and grades (0-100) for 10 core interview dimensions.
    Uses per-question feedback metrics when available, otherwise falls back to base score.
    """
    raw_metrics = raw_metrics or {}
    wpm = raw_metrics.get("wpm", 135)
    clarity = raw_metrics.get("clarity", 85)
    pauses = raw_metrics.get("pause_count", 2)
    sentiment = raw_metrics.get("sentiment", "positive")

    total_q = len(feedbacks) if feedbacks else 1
    avg_score_10 = sum([f.get("score", 7) for f in feedbacks]) / total_q if feedbacks else 7.5
    base_100 = round(avg_score_10 * 10)

    # Extract per-dimension averages from feedbacks where the AI returned them
    def avg_metric(key, fallback=None):
        vals = []
        for f in (feedbacks or []):
            m = f.get("metrics", {})
            v = m.get(key) if isinstance(m, dict) else None
            if v is not None:
                try:
                    vals.append(float(v) * 10)  # metrics stored as 0-10, convert to 0-100
                except Exception:
                    pass
        if vals:
            return min(100, max(0, round(sum(vals) / len(vals))))
        return fallback if fallback is not None else base_100

    scores = {
        # 1. Communication: from communication metric + speech clarity bonus
        "Communication": min(100, max(0, avg_metric("communication", base_100) + (5 if clarity >= 80 else -5) + (3 if 110 <= wpm <= 165 else 0))),
        # 2. Technical Knowledge: from technical_knowledge metric
        "Technical Knowledge": avg_metric("technical_knowledge", base_100),
        # 3. Problem Solving: from problem_solving metric
        "Problem Solving": avg_metric("problem_solving", base_100),
        # 4. Confidence: from confidence metric + pause penalty
        "Confidence": min(100, max(0, avg_metric("confidence", base_100) + (5 if pauses <= 2 else -8) + (3 if sentiment == "positive" else 0))),
        # 5. Behavioral Skills: from behavioral metric
        "Behavioral Skills": avg_metric("behavioral", base_100),
        # 6. Resume Knowledge: from resume_understanding metric
        "Resume Knowledge": avg_metric("resume_understanding", base_100),
        # 7. Project Explanation: from project_explanation metric
        "Project Explanation": avg_metric("project_explanation", base_100),
        # 8. Leadership: from leadership metric
        "Leadership": avg_metric("leadership", base_100),
        # 9. Grammar: based on clarity signal (not strongly penalized)
        "Grammar": min(100, max(0, (88 if clarity >= 85 else 76) + (5 if sentiment == "positive" else 0))),
        # 10. Vocabulary: from technical_knowledge as proxy for vocab richness
        "Vocabulary": min(100, max(0, avg_metric("technical_knowledge", 82) + (3 if base_100 >= 80 else -3)))
    }

    section_list = []
    for name, s_val in scores.items():
        g_info = calculate_grade_info(s_val)
        section_list.append({
            "name": name,
            "score": s_val,
            "grade": g_info["grade"],
            "color": g_info["color"],
            "bgColor": g_info["bgColor"],
            "label": g_info["label"]
        })

    return section_list

def award_badges(overall_score: float, sections: list) -> list:
    badges = []
    sec_dict = {s["name"]: s.get("score") for s in sections if isinstance(s.get("score"), (int, float))}

    if sec_dict.get("Communication", 0) >= 88:
        badges.append({"name": "Excellent Communicator", "icon": "🗣️", "desc": "Masterful clarity and articulation"})
    if sec_dict.get("Technical Knowledge", 0) >= 88:
        badges.append({"name": "Technical Expert", "icon": "💻", "desc": "Deep domain and engineering proficiency"})
    if sec_dict.get("Problem Solving", 0) >= 88:
        badges.append({"name": "Problem Solver", "icon": "🧩", "desc": "Structured and sharp analytical reasoning"})
    if sec_dict.get("Leadership", 0) >= 82:
        badges.append({"name": "Leadership Potential", "icon": "👑", "desc": "Strong ownership and decision-making"})
    if sec_dict.get("Project Explanation", 0) >= 85:
        badges.append({"name": "Project Specialist", "icon": "🚀", "desc": "Impactful project architecture walk-through"})
    if sec_dict.get("Behavioral Skills", 0) >= 85:
        badges.append({"name": "Behavioral Star", "icon": "⭐", "desc": "Effective STAR technique responses"})
    if overall_score >= 90:
        badges.append({"name": "Quick Learner", "icon": "⚡", "desc": "Adaptive candidate with high learning velocity"})
        badges.append({"name": "Creative Thinker", "icon": "💡", "desc": "Innovative problem formulation"})

    # Only give "Promising Candidate" if score >= 60 and no other badge was earned
    if not badges and overall_score >= 60:
        badges.append({"name": "Promising Candidate", "icon": "🌱", "desc": "Solid foundation ready for growth"})

    # No badges at all if performance is too low — don't hand out participation trophies
    return badges
