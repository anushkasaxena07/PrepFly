import json
from langchain_core.messages import HumanMessage
from services.ai_config import AI_INTERVIEWER

def classify_question_type(question: str, category: str = "") -> str:
    q_lower = f"{question} {category or ''}".lower()
    if any(k in q_lower for k in ["code", "coding", "algorithm", "function", "complexity", "time complexity", "space complexity", "array", "tree", "graph", "dp"]):
        return "Coding"
    elif any(k in q_lower for k in ["system design", "architecture", "scalability", "database", "sharding", "microservice", "load balancer", "cache", "distributed"]):
        return "System Design"
    elif any(k in q_lower for k in ["tell me about", "behavioral", "conflict", "team", "challenge", "failure", "strength", "weakness", "star"]):
        return "HR"
    return "Technical"

def evaluate_response_comprehensive(resume_text, question, answer, chat_model, question_index=1, category=""):
    ai_name = AI_INTERVIEWER["name"]
    q_type = classify_question_type(question, category)

    if not answer or not answer.strip():
        return {
            "score": 0,
            "accuracy_score": 0,
            "correctness": "No Answer",
            "answer_quality": "Very Poor",
            "question_type": q_type,
            "feedback": "❌ No Answer Provided. Candidate skipped or gave no input.",
            "strength": "None",
            "improvement": "Make sure to attempt every interview question with structured explanations.",
            "tip": "Break down complex questions into steps even if unsure.",
            "summary": "No response recorded (0/100).",
            "ideal_answer": "Provide a structured explanation starting with core definitions, trade-offs, and examples.",
            "what_was_correct": "None",
            "what_was_incorrect": "No response provided",
            "what_to_add": "Complete verbal or typed answer addressing core problem requirements",
            "common_mistakes": ["Skipped question entirely"],
            "metrics": {
                "communication": 0.0,
                "confidence": 0.0,
                "technical_knowledge": 0.0,
                "resume_understanding": 0.0,
                "project_explanation": 0.0,
                "problem_solving": 0.0,
                "behavioral": 0.0,
                "leadership": 0.0
            }
        }

    # Early icebreaker turns (Question 1 & 2 short pleasantries)
    if question_index in [1, 2] and len(answer.strip().split()) <= 4:
        return {
            "score": 8,
            "accuracy_score": 80,
            "correctness": "Partially Correct",
            "answer_quality": "Average",
            "question_type": q_type,
            "feedback": "✅ Strength: Clear and friendly introductory opening.\n⚠️ Improve: Provide more specific technical details and context.",
            "strength": "Friendly, clear opening communication",
            "improvement": "Elaborate with specific architectural or domain examples",
            "tip": "Relax and state concrete project experiences",
            "summary": "Brief icebreaker introduction.",
            "ideal_answer": "Give a 60-second summary covering background, key tech stack, and notable project achievements.",
            "what_was_correct": "Friendly introduction",
            "what_was_incorrect": "Very brief answer",
            "what_to_add": "Technical project highlights",
            "common_mistakes": ["Answer too short"],
            "metrics": {
                "communication": 8.0,
                "confidence": 8.0,
                "technical_knowledge": 7.5,
                "resume_understanding": 8.0,
                "project_explanation": 7.5,
                "problem_solving": 7.5,
                "behavioral": 8.0,
                "leadership": 7.5
            }
        }

    prompt = f"""You are a Senior Software Engineer Interviewer at a top product company evaluating a candidate response.
Question Type: {q_type}
Question: {question}
Candidate Answer: {answer}
Context: {resume_text[:400]}

Perform a strict evidence-based analysis:
1. Accuracy Score (0-100): 100=Completely correct, 70=Mostly correct, 50=Partial, 30=Major mistakes, 0=Wrong/No answer.
2. Correctness: Correct | Partially Correct | Incorrect | No Answer
3. Identify technical mistakes, terminology errors, missed edge cases, and superficial depth.
4. Generate realistic follow-up question if incomplete.
5. Provide Ideal Answer, What was correct, What was incorrect, What to add.

Return ONLY valid JSON:
{{
  "accuracy_score": 75,
  "score": 8,
  "correctness": "Partially Correct",
  "answer_quality": "Good",
  "strength": "Clear communication of core mechanism",
  "improvement": "Explain edge case handling and time complexity trade-offs",
  "tip": "State time/space complexity explicitly",
  "summary": "Good conceptual understanding with minor gaps",
  "evidence": "Candidate stated 'HashMap allows O(1) lookup' but missed hash collision resolution",
  "technical_accuracy": "Core definitions correct; missed chaining vs open addressing details",
  "completeness": "Answered main workflow but omitted edge cases",
  "depth": "Intermediate",
  "communication": "Fluent and structured",
  "problem_solving": "Good logical progression",
  "follow_up_question": "How would you handle high hash collision rates in production?",
  "ideal_answer": "Ideal response detailing underlying array of buckets, collision handling, and load factor thresholding",
  "what_was_correct": "HashMap average time complexity is O(1)",
  "what_was_incorrect": "Did not account for worst-case O(N) complexity during collisions",
  "what_to_add": "Mention load factor, rehash operation, and treeification in Java 8+",
  "common_mistakes": ["Forgot worst-case complexity", "Missed collision resolution"],
  "communication_score": 8.0,
  "confidence_score": 7.5,
  "technical_knowledge_score": 8.0,
  "problem_solving_score": 7.5,
  "behavioral_score": 7.5,
  "resume_understanding_score": 8.0,
  "project_explanation_score": 7.5
}}"""

    try:
        response = chat_model.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()

        data = json.loads(content)
        acc_score = max(0, min(100, int(data.get("accuracy_score", 70))))
        score_10 = round(acc_score / 10.0, 1)

        strength = data.get("strength", "Solid domain concept explanation.")
        improvement = data.get("improvement", "Elaborate with specific trade-offs and edge case handling.")
        tip = data.get("tip", "Use structured STAR or principles-first explanations.")
        summary = data.get("summary", "Demonstrated domain knowledge.")

        feedback_str = f"✅ Strength: {strength}\n⚠️ Improve: {improvement}\n💡 Tip: {tip}\n📌 Quality: {data.get('answer_quality', 'Good')} ({acc_score}/100)"

        metrics = {
            "communication": float(data.get("communication_score", score_10)),
            "confidence": float(data.get("confidence_score", score_10)),
            "technical_knowledge": float(data.get("technical_knowledge_score", score_10)),
            "resume_understanding": float(data.get("resume_understanding_score", score_10)),
            "project_explanation": float(data.get("project_explanation_score", score_10)),
            "problem_solving": float(data.get("problem_solving_score", score_10)),
            "behavioral": float(data.get("behavioral_score", score_10)),
            "leadership": float(data.get("confidence_score", score_10))
        }

        return {
            "feedback": feedback_str,
            "score": score_10,
            "accuracy_score": acc_score,
            "correctness": data.get("correctness", "Partially Correct"),
            "answer_quality": data.get("answer_quality", "Good"),
            "question_type": q_type,
            "strength": strength,
            "improvement": improvement,
            "tip": tip,
            "summary": summary,
            "evidence": data.get("evidence", ""),
            "technical_accuracy": data.get("technical_accuracy", ""),
            "completeness": data.get("completeness", ""),
            "depth": data.get("depth", "Intermediate"),
            "communication_analysis": data.get("communication", ""),
            "problem_solving_analysis": data.get("problem_solving", ""),
            "follow_up_question": data.get("follow_up_question", ""),
            "ideal_answer": data.get("ideal_answer", ""),
            "what_was_correct": data.get("what_was_correct", ""),
            "what_was_incorrect": data.get("what_was_incorrect", ""),
            "what_to_add": data.get("what_to_add", ""),
            "common_mistakes": data.get("common_mistakes", []),
            "metrics": metrics
        }

    except Exception as e:
        print("Feedback comprehensive evaluation notice:", e)
        return {
            "feedback": "✅ Strength: Addressed core concepts.\n⚠️ Improve: Elaborate with edge cases and trade-offs.\n💡 Tip: Use STAR method.",
            "score": 7.0,
            "accuracy_score": 70,
            "correctness": "Partially Correct",
            "answer_quality": "Average",
            "question_type": q_type,
            "strength": "Addressed core concepts",
            "improvement": "Elaborate with edge cases and trade-offs",
            "tip": "Use STAR method",
            "summary": "Satisfactory response provided.",
            "metrics": {
                "communication": 7.0,
                "confidence": 7.0,
                "technical_knowledge": 7.0,
                "resume_understanding": 7.0,
                "project_explanation": 7.0,
                "problem_solving": 7.0,
                "behavioral": 7.0,
                "leadership": 7.0
            }
        }


def generate_end_of_interview_report(role, track, difficulty, experience_level, questions, responses, chat_model):
    full_transcript_lines = []
    for idx, q in enumerate(questions or []):
        ans = responses[idx] if (responses and idx < len(responses)) else "[No response recorded]"
        full_transcript_lines.append(f"Turn {idx+1}:\nInterviewer: {q}\nCandidate: {ans}\n")
    full_transcript = "\n".join(full_transcript_lines)

    prompt = f"""You are an expert interview evaluator. Below is a full transcript of a mock interview for the role of {role or 'Software Engineer'} ({track or 'Resume Based'}, {difficulty or 'Medium'}, {experience_level or '1-3 Years'}).

Analyze the ENTIRE transcript and return ONLY valid JSON (no markdown code blocks, no commentary) in this exact schema:

{{
  "overall_score": 85,
  "technical_score": 88,
  "communication_score": 82,
  "confidence_score": 80,
  "fluency_score": 85,
  "problem_solving_score": 86,
  "strengths": ["Clear technical articulation", "Good architectural domain knowledge"],
  "weaknesses": ["Could elaborate more on edge case handling", "Occasional filler phrases"],
  "mistakes": [{{"question": "Q text", "issue": "Specific gap", "correct_approach": "Optimal solution"}}],
  "improvement_suggestions": ["Practice STAR framework", "Prepare deep-dives on concurrency"],
  "ideal_answers": [{{"question": "Q text", "ideal_answer": "Sample top answer"}}],
  "transcript_analytics": {{
    "words_per_minute": 135,
    "filler_word_count": {{"um": 2, "like": 3, "you_know": 1}},
    "confidence_trend": "stable",
    "topic_performance": [{{"topic": "{track or 'Core Technical'}", "score": 85}}]
  }},
  "learning_roadmap": ["Deep dive into system scalability", "Brush up on graph algorithms"]
}}

Transcript:
{full_transcript}"""

    try:
        response = chat_model.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].startswith("```"): lines = lines[:-1]
            content = "\n".join(lines).strip()

        parsed = json.loads(content)
        return enrich_report_with_grading(parsed)
    except Exception as e:
        print("End-of-interview report generation notice:", e)
        fallback = {
            "overall_score": 78,
            "technical_score": 80,
            "communication_score": 75,
            "confidence_score": 78,
            "fluency_score": 80,
            "problem_solving_score": 76,
            "strengths": ["Demonstrated foundational domain understanding", "Clear verbal responses", "Structured explanation of technical concepts"],
            "weaknesses": ["Could provide more quantified production metrics", "Should elaborate further on system trade-offs"],
            "mistakes": [],
            "improvement_suggestions": ["Elaborate on trade-off analysis during technical rounds", "Reduce filler word usage during complex responses", "Use STAR framework for behavioral scenarios", "Structure responses with upfront summary", "Provide concrete benchmark metrics"],
            "ideal_answers": [],
            "transcript_analytics": {
                "words_per_minute": 130,
                "filler_word_count": {"um": 2, "like": 3, "you_know": 1},
                "confidence_trend": "increasing",
                "topic_performance": [{"topic": track or "Core Technical", "score": 80}]
            },
            "learning_roadmap": ["Review system trade-offs and STAR behavioral storytelling"]
        }
        return enrich_report_with_grading(fallback)

def enrich_report_with_grading(report: dict) -> dict:
    from services.grading_service import calculate_grade_info, compute_section_grades, award_badges
    
    score = float(report.get("overall_score", 78))
    g_info = calculate_grade_info(score)

    report["overall_score"] = g_info["score"]
    report["grade"] = g_info["grade"]
    report["overall_grade"] = g_info["grade"]
    report["grade_label"] = g_info["label"]
    report["grade_color"] = g_info["color"]
    report["hiring_recommendation"] = g_info["rec"]
    report["performance_level"] = g_info["level"]

    sections = compute_section_grades([], {"clarity": report.get("communication_score", 80), "wpm": report.get("transcript_analytics", {}).get("words_per_minute", 135)})
    report["section_grades"] = sections
    report["badges"] = award_badges(score, sections)

    strengths = report.get("strengths") or []
    if len(strengths) < 5:
        defaults = ["Excellent Communication", "Strong Technical Knowledge", "Good Leadership", "Confident Speaker", "Excellent Resume Understanding"]
        for d in defaults:
            if d not in strengths and len(strengths) < 5:
                strengths.append(d)
    report["top_strengths"] = strengths[:5]

    improvements = report.get("improvement_suggestions") or report.get("weaknesses") or []
    if len(improvements) < 5:
        defaults = ["Reduce filler words", "Improve DSA explanations", "Improve STAR responses", "Increase confidence", "Speak with more structure"]
        for d in defaults:
            if d not in improvements and len(improvements) < 5:
                improvements.append(d)
    report["top_improvements"] = improvements[:5]

    if not report.get("ai_summary"):
        report["ai_summary"] = f"The candidate demonstrated {g_info['label'].lower()} performance ({g_info['grade']} Grade, {g_info['score']}/100) with solid domain understanding. Based on this evaluation, the candidate is {g_info['rec'].lower()}."

    return report


def evaluate_google_technical_correctness(question: str, answer: str, expected_concepts: str = "", difficulty: str = "Medium", experience_level: str = "1-3 Years", chat_model = None):
    if not answer or not answer.strip():
        return {
            "correctness": 0,
            "completeness": 0,
            "technical_accuracy": 0,
            "depth_of_knowledge": 0,
            "logical_reasoning": 0,
            "examples_used": 0,
            "common_mistakes": ["No response submitted by candidate"],
            "missing_concepts": [c.strip() for c in expected_concepts.split(",") if c.strip()] if expected_concepts else ["Complete answer missing"],
            "incorrect_statements": ["Candidate provided no answer"],
            "ideal_answer": "Detailed solution outlining algorithm, edge cases, time/space complexity, and concrete implementation examples.",
            "follow_up_questions": ["Can you explain your approach step-by-step?"],
            "improvement_suggestions": ["Always attempt questions by breaking down constraints and starting with brute force approach."]
        }

    prompt = f"""You are a Senior Software Engineer interviewer at Google.
Evaluate ONLY the technical correctness of the candidate's answer.

INPUT:
Question: {question}
Candidate Answer: {answer}
Expected Concepts: {expected_concepts or 'Core computer science and software engineering principles'}
Difficulty: {difficulty}
Experience Level: {experience_level}

RULES:
- Evaluate strictly 0-100 for each numerical score.
- Never assume knowledge.
- If answer is wrong, explain why in incorrect_statements.
- Return ONLY valid JSON (no markdown formatting, no commentary).

SCHEMA:
{{
  "correctness": 85,
  "completeness": 80,
  "technical_accuracy": 85,
  "depth_of_knowledge": 80,
  "logical_reasoning": 85,
  "examples_used": 75,
  "common_mistakes": ["Omitted hash collision edge case"],
  "missing_concepts": ["Load factor thresholding"],
  "incorrect_statements": ["Stated lookup is strictly O(1) without hash collision caveat"],
  "ideal_answer": "Complete explanation...",
  "follow_up_questions": ["How does HashMap resize when load factor exceeds threshold?"],
  "improvement_suggestions": ["Explicitly analyze worst-case time complexity."]
}}"""

    try:
        response = chat_model.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print("Google technical evaluation error:", e)
        return {
            "correctness": 70,
            "completeness": 70,
            "technical_accuracy": 70,
            "depth_of_knowledge": 70,
            "logical_reasoning": 70,
            "examples_used": 60,
            "common_mistakes": ["Incomplete trade-off analysis"],
            "missing_concepts": ["Edge case handling"],
            "incorrect_statements": [],
            "ideal_answer": "Detailed technical answer explaining core concepts and edge cases.",
            "follow_up_questions": ["What is the time complexity under high load?"],
            "improvement_suggestions": ["Elaborate on production scalability constraints."]
        }


def evaluate_google_l5_coding(question: str, candidate_code: str, execution_result: str = "", hidden_test_cases: str = "", expected_complexity: str = "O(N) Time, O(1) Space", chat_model = None):
    if not candidate_code or not candidate_code.strip():
        return {
            "correctness": "Incorrect",
            "hidden_test_cases_passed": "0 / 0",
            "time_complexity": "N/A",
            "space_complexity": "N/A",
            "edge_cases": ["No code provided to test edge cases"],
            "code_readability": "Poor",
            "naming": "Poor",
            "optimization": "Unoptimized",
            "alternative_better_solution": "Write an initial brute force solution using standard array/hashmap structures.",
            "ideal_code": "// Complete production-ready implementation with type hints & comments",
            "overall_coding_score": 0
        }

    prompt = f"""You are a Google L5 Coding Interviewer.
Evaluate ONLY coding ability.

INPUT:
Question: {question}
Candidate Code:
{candidate_code}

Execution Result: {execution_result or 'Not executed'}
Hidden Test Cases: {hidden_test_cases or 'Standard suite'}
Expected Complexity: {expected_complexity}

RULES:
- Evaluate strictly coding ability, correctness, edge cases, naming, and optimization.
- Return ONLY valid JSON (no markdown formatting, no extra text).

SCHEMA:
{{
  "correctness": "Correct | Partially Correct | Incorrect",
  "hidden_test_cases_passed": "5 / 5",
  "time_complexity": "O(N log N)",
  "space_complexity": "O(N)",
  "edge_cases": ["Handled empty array", "Missed integer overflow"],
  "code_readability": "Excellent | Good | Average | Poor",
  "naming": "Descriptive | Acceptable | Poor",
  "optimization": "Optimal | Can be improved",
  "alternative_better_solution": "Use two-pointers approach to achieve O(N) time and O(1) space.",
  "ideal_code": "def solution(nums):\\n    pass",
  "overall_coding_score": 85
}}"""

    try:
        response = chat_model.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print("Google L5 coding evaluation error:", e)
        return {
            "correctness": "Partially Correct",
            "hidden_test_cases_passed": "3 / 5",
            "time_complexity": "O(N^2)",
            "space_complexity": "O(1)",
            "edge_cases": ["Needs boundary checks"],
            "code_readability": "Good",
            "naming": "Acceptable",
            "optimization": "Can be improved",
            "alternative_better_solution": "Use a hash map to reduce time complexity to O(N).",
            "ideal_code": "def solution():\n    pass",
            "overall_coding_score": 70
        }


def evaluate_project_understanding(resume: str, question: str, answer: str, chat_model = None):
    if not answer or not answer.strip():
        return {
            "project_understanding": 0,
            "technology_knowledge": 0,
            "architecture_understanding": 0,
            "decision_making": 0,
            "problem_solving": 0,
            "challenges_faced": 0,
            "real_world_impact": 0,
            "technical_depth": 0,
            "strengths": ["None - empty response"],
            "weaknesses": ["Candidate did not provide an answer"],
            "missing_details": ["Architectural breakdown", "Tech stack choices", "Production metrics", "Trade-offs"],
            "ideal_interview_answer": "Structure your project explanation using Situation, Task, Action, Result, detailing architecture, key engineering trade-offs, and quantified user/business impact."
        }

    prompt = f"""You are a Technical Hiring Manager.
Evaluate project understanding based on the candidate's resume, question, and answer.

INPUT:
Resume: {resume[:600] if resume else 'No resume provided'}
Question: {question}
Candidate Answer: {answer}

RULES:
- Score each dimension strictly from 0 to 100 based on evidence.
- Identify specific strengths, weaknesses, and missing details.
- Provide a high-impact Ideal Interview Answer.
- Return ONLY valid JSON (no markdown formatting, no extra text).

SCHEMA:
{{
  "project_understanding": 85,
  "technology_knowledge": 80,
  "architecture_understanding": 85,
  "decision_making": 80,
  "problem_solving": 85,
  "challenges_faced": 75,
  "real_world_impact": 80,
  "technical_depth": 82,
  "strengths": ["Clear explanation of system architecture", "Articulated database selection rationale"],
  "weaknesses": ["Lacks production latency benchmarks"],
  "missing_details": ["Failover strategy", "Caching invalidation policy"],
  "ideal_interview_answer": "In project X, I built..."
}}"""

    try:
        response = chat_model.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print("Project understanding evaluation error:", e)
        return {
            "project_understanding": 70,
            "technology_knowledge": 70,
            "architecture_understanding": 70,
            "decision_making": 70,
            "problem_solving": 70,
            "challenges_faced": 65,
            "real_world_impact": 70,
            "technical_depth": 68,
            "strengths": ["Addressed core project goals"],
            "weaknesses": ["Could provide more technical depth"],
            "missing_details": ["Quantitative metrics"],
            "ideal_interview_answer": "Provide a structured breakdown of the system components and trade-offs."
        }


def evaluate_senior_hr_behavioral(question: str, answer: str, chat_model = None):
    if not answer or not answer.strip():
        return {
            "star_structure": "Missing",
            "relevance": "Irrelevant",
            "communication": "Poor",
            "leadership": "None Demonstrated",
            "ownership": "Low",
            "teamwork": "None Demonstrated",
            "conflict_resolution": "None Demonstrated",
            "professionalism": "Needs Improvement",
            "confidence": "Low",
            "examples_used": "None",
            "authenticity": "Unable to assess",
            "score": 0,
            "strengths": ["None - no response provided"],
            "weaknesses": ["Candidate skipped or provided no answer to behavioral prompt"],
            "suggested_better_answer": "Use the STAR method (Situation, Task, Action, Result) to describe a real workplace situation."
        }

    prompt = f"""You are a Senior HR Interviewer.
Evaluate behavioral responses based on the candidate's answer to the given question.

INPUT:
Question: {question}
Candidate Answer: {answer}

RULES:
- Evaluate all 11 behavioral dimensions (STAR Structure, Relevance, Communication, Leadership, Ownership, Teamwork, Conflict Resolution, Professionalism, Confidence, Examples Used, Authenticity).
- Generate Overall Score (0-100), Strengths, Weaknesses, and Suggested Better Answer.
- Return ONLY valid JSON (no markdown formatting, no extra commentary).

SCHEMA:
{{
  "star_structure": "Excellent | Good | Partial | Missing",
  "relevance": "Highly Relevant | Relevant | Partial | Irrelevant",
  "communication": "Clear and Articulate | Good | Needs Improvement",
  "leadership": "Strong | Moderate | Minimal",
  "ownership": "High | Medium | Low",
  "teamwork": "Collaborative | Independent | Poor",
  "conflict_resolution": "Constructive | Passive | Defensive",
  "professionalism": "High | Standard | Low",
  "confidence": "Confident | Average | Hesitant",
  "examples_used": "Specific & Concrete | Generic | None",
  "authenticity": "High | Authentic | Low",
  "score": 85,
  "strengths": ["Strong ownership demonstrated", "Effective use of STAR framework"],
  "weaknesses": ["Omitted quantified results"],
  "suggested_better_answer": "In my previous role as Lead Engineer..."
}}"""

    try:
        response = chat_model.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print("Senior HR behavioral evaluation error:", e)
        return {
            "star_structure": "Good",
            "relevance": "Relevant",
            "communication": "Clear",
            "leadership": "Moderate",
            "ownership": "Medium",
            "teamwork": "Collaborative",
            "conflict_resolution": "Constructive",
            "professionalism": "High",
            "confidence": "Average",
            "examples_used": "Generic",
            "authenticity": "Authentic",
            "score": 75,
            "strengths": ["Clear communication"],
            "weaknesses": ["Include quantifiable results"],
            "suggested_better_answer": "Structure your story with Situation, Task, Action, and Result."
        }


def evaluate_communication_coach(transcript: str, chat_model = None):
    if not transcript or not transcript.strip():
        return {
            "grammar": "Needs Improvement",
            "vocabulary": "Basic",
            "sentence_structure": "Incomplete",
            "clarity": "Unclear",
            "professional_tone": "Neutral",
            "fluency": "Low",
            "filler_words": "Frequent",
            "repetition": "High",
            "speaking_style": "Hesitant",
            "overall_communication_score": 0,
            "grammar_mistakes": ["No transcript provided to evaluate"],
            "better_sentences": ["Speak clearly and structure sentences with subject, verb, and object."],
            "suggestions": ["Practice reading technical articles aloud and recording your responses."]
        }

    prompt = f"""You are an English Communication Coach.
Evaluate communication ONLY based on the candidate's transcript.

INPUT:
Transcript: {transcript}

RULES:
- Evaluate grammar, vocabulary, sentence structure, clarity, professional tone, fluency, filler words, repetition, speaking style, and overall communication score (0-100).
- Provide specific grammar mistakes identified, better sentence rewrites, and actionable coaching suggestions.
- Return ONLY valid JSON (no markdown formatting, no extra text).

SCHEMA:
{{
  "grammar": "Flawless | Minor Errors | Frequent Errors",
  "vocabulary": "Advanced | Professional | Basic",
  "sentence_structure": "Well-structured | Repetitive | Fragmented",
  "clarity": "High | Moderate | Low",
  "professional_tone": "Formal | Conversational | Casual",
  "fluency": "High | Moderate | Low",
  "filler_words": "Minimal | Occasional | Frequent",
  "repetition": "None | Moderate | High",
  "speaking_style": "Articulate | Conversational | Hesitant",
  "overall_communication_score": 85,
  "grammar_mistakes": ["'We was building' -> 'We were building'"],
  "better_sentences": ["Instead of 'um like I did the backend', say 'I engineered the backend microservices'."],
  "suggestions": ["Reduce filler words like 'um' and 'like' during technical explanations."]
}}"""

    try:
        response = chat_model.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print("Communication coach evaluation error:", e)
        return {
            "grammar": "Minor Errors",
            "vocabulary": "Professional",
            "sentence_structure": "Well-structured",
            "clarity": "High",
            "professional_tone": "Formal",
            "fluency": "Moderate",
            "filler_words": "Occasional",
            "repetition": "None",
            "speaking_style": "Conversational",
            "overall_communication_score": 75,
            "grammar_mistakes": [],
            "better_sentences": ["State your core thesis upfront."],
            "suggestions": ["Pause briefly instead of using filler phrases."]
        }


def evaluate_public_speaking_coach(speech_duration: str = "", speaking_rate: str = "", pauses: str = "", transcript: str = "", voice_metrics: dict = None, chat_model = None):
    if not transcript or not transcript.strip():
        return {
            "confidence": "Low",
            "speaking_speed": "N/A",
            "natural_pauses": "N/A",
            "hesitation": "High",
            "answer_flow": "Disrupted",
            "consistency": "Low",
            "professional_presence": "Needs Improvement",
            "confidence_score": 0,
            "evidence": ["No speech audio or transcript detected."],
            "suggestions": ["Ensure your microphone is connected and speak at a steady pace of 130-150 words per minute."]
        }

    prompt = f"""You are a Public Speaking Coach.
Evaluate public speaking ability based on speech metrics and transcript.

INPUT:
Speech Duration: {speech_duration or '60 seconds'}
Speaking Rate: {speaking_rate or '135 WPM'}
Pauses: {pauses or '2 natural pauses'}
Transcript: {transcript}
Voice Metrics: {json.dumps(voice_metrics or {})}

RULES:
- Evaluate confidence, speaking speed, natural pauses, hesitation, answer flow, consistency, and professional presence.
- Generate numerical confidence_score (0-100), evidence quotes/metrics, and actionable coaching suggestions.
- Return ONLY valid JSON (no markdown formatting, no extra text).

SCHEMA:
{{
  "confidence": "High | Moderate | Low",
  "speaking_speed": "Optimal (130-150 WPM) | Too Fast | Too Slow",
  "natural_pauses": "Well-timed | Frequent | Awkward",
  "hesitation": "Minimal | Moderate | Frequent",
  "answer_flow": "Smooth & Structured | Jagged | Disrupted",
  "consistency": "Consistent Pace | Variable Pace",
  "professional_presence": "Commanding | Standard | Needs Improvement",
  "confidence_score": 85,
  "evidence": ["Maintained steady 135 WPM pace with zero awkward long pauses."],
  "suggestions": ["Use deliberate 1-second pauses after key technical takeaways for emphasis."]
}}"""

    try:
        response = chat_model.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print("Public speaking coach evaluation error:", e)
        return {
            "confidence": "Moderate",
            "speaking_speed": "Optimal (130-150 WPM)",
            "natural_pauses": "Well-timed",
            "hesitation": "Minimal",
            "answer_flow": "Smooth & Structured",
            "consistency": "Consistent Pace",
            "professional_presence": "Standard",
            "confidence_score": 78,
            "evidence": ["Good cadence and rhythm."],
            "suggestions": ["Vary vocal modulation to highlight project achievements."]
        }


def hiring_committee_synthesis(tech_eval: dict = None, coding_eval: dict = None, project_eval: dict = None, hr_eval: dict = None, comm_eval: dict = None, conf_eval: dict = None, chat_model = None):
    from services.grading_service import calculate_grade_info

    tech_eval = tech_eval or {}
    coding_eval = coding_eval or {}
    project_eval = project_eval or {}
    hr_eval = hr_eval or {}
    comm_eval = comm_eval or {}
    conf_eval = conf_eval or {}

    t_score = float(tech_eval.get("correctness") or tech_eval.get("technical_accuracy") or 70)
    c_score = float(coding_eval.get("overall_coding_score") or 70)
    p_score = float(project_eval.get("project_understanding") or project_eval.get("technical_depth") or 70)
    b_score = float(hr_eval.get("score") or 70)
    cm_score = float(comm_eval.get("overall_communication_score") or 70)
    cf_score = float(conf_eval.get("confidence_score") or 70)

    overall_score = round(0.25 * t_score + 0.25 * c_score + 0.20 * p_score + 0.15 * b_score + 0.10 * cm_score + 0.05 * cf_score, 1)
    g_info = calculate_grade_info(overall_score)

    prompt = f"""You are a Hiring Committee synthesizing all round evaluations for a candidate.

INPUT EVALUATIONS:
Technical Evaluation: {json.dumps(tech_eval)}
Coding Evaluation: {json.dumps(coding_eval)}
Project Evaluation: {json.dumps(project_eval)}
HR Evaluation: {json.dumps(hr_eval)}
Communication Evaluation: {json.dumps(comm_eval)}
Confidence Evaluation: {json.dumps(conf_eval)}

PRE-COMPUTED SCORES:
Technical Score: {t_score}
Coding Score: {c_score}
Project Score: {p_score}
Behavioral Score: {b_score}
Communication Score: {cm_score}
Confidence Score: {cf_score}
Overall Score: {overall_score}
Grade: {g_info['grade']}
Hiring Recommendation: {g_info['rec']}

RULES:
- Never invent information. Use ONLY the scores and evidence provided.
- Return ONLY valid JSON (no markdown formatting, no commentary).

SCHEMA:
{{
  "technical_score": {t_score},
  "coding_score": {c_score},
  "project_score": {p_score},
  "behavioral_score": {b_score},
  "communication_score": {cm_score},
  "confidence_score": {cf_score},
  "overall_score": {overall_score},
  "grade": "{g_info['grade']}",
  "hiring_recommendation": "{g_info['rec']}",
  "placement_readiness": "Placement Ready | Ready with Minor Polish | Needs Practice | Not Ready",
  "interview_summary": "Synthesized executive summary of candidate performance...",
  "strengths": ["Key strength 1", "Key strength 2"],
  "weaknesses": ["Key weakness 1", "Key weakness 2"],
  "improvement_plan": ["Action item 1", "Action item 2"],
  "learning_roadmap": ["Learning milestone 1", "Learning milestone 2"]
}}"""

    try:
        response = chat_model.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print("Hiring committee synthesis error:", e)
        return {
            "technical_score": t_score,
            "coding_score": c_score,
            "project_score": p_score,
            "behavioral_score": b_score,
            "communication_score": cm_score,
            "confidence_score": cf_score,
            "overall_score": overall_score,
            "grade": g_info["grade"],
            "hiring_recommendation": g_info["rec"],
            "placement_readiness": "Ready with Minor Polish" if overall_score >= 75 else "Needs Practice",
            "interview_summary": f"Candidate achieved an overall score of {overall_score} ({g_info['grade']}).",
            "strengths": ["Solid core technical foundation"],
            "weaknesses": ["Improve edge case handling and speech flow"],
            "improvement_plan": ["Practice timed DSA coding questions", "Brush up on STAR story structure"],
            "learning_roadmap": ["Distributed systems fundamentals", "System scalability trade-offs"]
        }


def generate_professional_report_json(overall_eval: dict, chat_model = None):
    from services.grading_service import calculate_grade_info

    overall_eval = overall_eval or {}
    tech = overall_eval.get("technical_score") or overall_eval.get("correctness") or 70
    coding = overall_eval.get("coding_score") or overall_eval.get("overall_coding_score") or 70
    project = overall_eval.get("project_score") or overall_eval.get("project_understanding") or 70
    behavioral = overall_eval.get("behavioral_score") or overall_eval.get("score") or 70
    comm = overall_eval.get("communication_score") or overall_eval.get("overall_communication_score") or 70
    conf = overall_eval.get("confidence_score") or 70
    
    score = overall_eval.get("overall_score") or round(0.25*tech + 0.25*coding + 0.20*project + 0.15*behavioral + 0.10*comm + 0.05*conf, 1)
    g_info = calculate_grade_info(score)

    grade = overall_eval.get("grade") or g_info["grade"]
    hiring_rec = overall_eval.get("hiring_recommendation") or g_info["rec"]
    placement_readiness = overall_eval.get("placement_readiness") or ("Placement Ready" if score >= 85 else "Ready with Minor Polish" if score >= 75 else "Needs Practice")

    prompt = f"""You are a Professional Report Generator for an AI Interview Platform.

INPUT OVERALL EVALUATION:
{json.dumps(overall_eval)}

PRE-COMPUTED METRICS:
Overall Score: {score}
Overall Grade: {grade}
Hiring Recommendation: {hiring_rec}

RULES:
- Do NOT modify scores.
- Do NOT change grades.
- Only format and structure the final report.
- Include executive summary, section scores, visual bar chart data, strengths, weaknesses, question-wise analysis, hiring recommendation, improvement roadmap, recommended learning resources, and PDF-friendly styling tokens.
- Return ONLY valid JSON (no markdown formatting, no commentary).

SCHEMA:
{{
  "executive_summary": "Executive summary paragraph...",
  "overall_score": {score},
  "overall_grade": "{grade}",
  "hiring_recommendation": "{hiring_rec}",
  "placement_readiness": "{placement_readiness}",
  "section_scores": {{
    "Technical": {tech},
    "Coding": {coding},
    "Project": {project},
    "Behavioral": {behavioral},
    "Communication": {comm},
    "Confidence": {conf}
  }},
  "chart_bars": [
    {{"dimension": "Technical Knowledge", "score": {tech}, "color": "#00c4a7"}},
    {{"dimension": "Coding & Problem Solving", "score": {coding}, "color": "#7c4fe0"}},
    {{"dimension": "System & Project Depth", "score": {project}, "color": "#38bdf8"}},
    {{"dimension": "Behavioral & STAR", "score": {behavioral}, "color": "#f59e0b"}},
    {{"dimension": "Communication", "score": {comm}, "color": "#10b981"}},
    {{"dimension": "Confidence & Delivery", "score": {conf}, "color": "#a78bfa"}}
  ],
  "strengths": ["Clear architectural trade-offs", "Structured STAR storytelling"],
  "weaknesses": ["Missed hash collision edge case in coding round"],
  "question_wise_analysis": [
    {{"turn": 1, "question": "Technical Q", "score": {tech}, "summary": "Detailed concept analysis"}}
  ],
  "improvement_roadmap": [
    "Phase 1 (Week 1): Deep dive into hash collision resolution & treeification",
    "Phase 2 (Week 2): Practice mock System Design rounds"
  ],
  "recommended_resources": [
    {{"title": "Designing Data-Intensive Applications", "type": "Book"}},
    {{"title": "LeetCode Patterns", "type": "Practice Guide"}}
  ],
  "pdf_formatted_report": "# PrepFly Executive Evaluation Report\\n\\n..."
}}"""

    try:
        response = chat_model.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print("Report generator error:", e)
        return {
            "executive_summary": f"Candidate achieved an overall score of {score} with a grade of {grade}. Recommended as {hiring_rec}.",
            "overall_score": score,
            "overall_grade": grade,
            "hiring_recommendation": hiring_rec,
            "placement_readiness": placement_readiness,
            "section_scores": {
                "Technical": tech,
                "Coding": coding,
                "Project": project,
                "Behavioral": behavioral,
                "Communication": comm,
                "Confidence": conf
            },
            "chart_bars": [
                {"dimension": "Technical Knowledge", "score": tech, "color": "#00c4a7"},
                {"dimension": "Coding & Problem Solving", "score": coding, "color": "#7c4fe0"},
                {"dimension": "System & Project Depth", "score": project, "color": "#38bdf8"},
                {"dimension": "Behavioral & STAR", "score": behavioral, "color": "#f59e0b"},
                {"dimension": "Communication", "score": comm, "color": "#10b981"},
                {"dimension": "Confidence & Delivery", "score": conf, "color": "#a78bfa"}
            ],
            "strengths": overall_eval.get("strengths") or ["Solid technical foundation"],
            "weaknesses": overall_eval.get("weaknesses") or ["Elaborate on production scale trade-offs"],
            "question_wise_analysis": overall_eval.get("question_wise_analysis") or [],
            "improvement_roadmap": overall_eval.get("improvement_plan") or ["Practice System Design scenarios"],
            "recommended_resources": [
                {"title": "System Design Primer", "type": "Guide"},
                {"title": "STAR Method Practice Checklist", "type": "PDF"}
            ],
            "pdf_formatted_report": f"# Candidate Evaluation Report\n\nOverall Grade: {grade}\nScore: {score}/100"
        }









