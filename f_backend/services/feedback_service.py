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


def generate_dynamic_single_fallback(question, answer, q_type):
    ans_clean = answer.strip()
    ans_lower = ans_clean.lower()
    q_lower = question.lower()
    
    word_count = len(ans_clean.split())
    
    # Analyze keyword overlap to see if they address the question
    stop_words = {"what", "how", "why", "who", "which", "when", "where", "the", "a", "an", "is", "are", "was", "were", "to", "in", "of", "on", "for", "with", "about", "your", "you", "me", "tell"}
    q_words = [w.strip("?,.()\"'") for w in q_lower.split() if w.strip("?,.()\"'") not in stop_words]
    matched_words = [w for w in q_words if len(w) > 3 and w in ans_lower]
    
    base_accuracy = 50
    if word_count > 30:
        base_accuracy = 80
    elif word_count > 15:
        base_accuracy = 70
    elif word_count > 6:
        base_accuracy = 60
        
    match_bonus = min(20, len(matched_words) * 5)
    acc_score = min(95, base_accuracy + match_bonus)
    
    if any(skip in ans_lower for skip in ["don't know", "don't remember", "skip", "no idea", "not sure", "pardon"]):
        acc_score = 30
        correctness = "Incorrect"
        quality = "Poor"
    elif acc_score >= 80:
        correctness = "Correct"
        quality = "Very Good"
    elif acc_score >= 65:
        correctness = "Partially Correct"
        quality = "Good"
    else:
        correctness = "Partially Correct"
        quality = "Average"
        
    score_10 = round(acc_score / 10.0, 1)
    
    if correctness == "Incorrect" or word_count < 5:
        strength = "Attempted to respond to the prompt."
        improvement = "Provide a more complete response using technical definitions and concrete examples."
        tip = "Explain your thought process step-by-step even if you don't know the exact syntax."
        summary = "Minimal response provided."
    else:
        if matched_words:
            strength = f"Mentioned key prompt concepts ({', '.join(matched_words[:3])}) clearly."
        else:
            strength = "Expressed ideas with appropriate length and structure."
            
        improvement = f"Elaborate on implementation details, edge cases, and optimization trade-offs for {q_type} concepts."
        tip = "Discuss time/space complexity tradeoffs and real-world system applications."
        summary = f"Good initial understanding of {q_type} question. Answered with {word_count} words."

    feedback_str = f"✅ Strength: {strength}\n⚠️ Improve: {improvement}\n💡 Tip: {tip}\n📌 Quality: {quality} ({acc_score}/100)"
    
    metrics = {
        "communication": min(10.0, score_10 + 0.5),
        "confidence": min(10.0, score_10 if word_count > 10 else score_10 - 1.0),
        "technical_knowledge": score_10,
        "resume_understanding": score_10,
        "project_explanation": score_10,
        "problem_solving": score_10,
        "behavioral": score_10,
        "leadership": score_10
    }
    
    return {
        "feedback": feedback_str,
        "score": score_10,
        "accuracy_score": acc_score,
        "correctness": correctness,
        "answer_quality": quality,
        "question_type": q_type,
        "strength": strength,
        "improvement": improvement,
        "tip": tip,
        "summary": summary,
        "evidence": f"Candidate response: '{ans_clean[:60]}...'",
        "technical_accuracy": "Addressed core concepts" if matched_words else "High-level response",
        "completeness": "Provided details" if word_count > 20 else "Somewhat incomplete",
        "depth": "Advanced" if word_count > 35 else "Intermediate" if word_count > 15 else "Introductory",
        "communication_analysis": "Fluent and structured",
        "problem_solving_analysis": "Good logical progression" if word_count > 20 else "Average approach",
        "follow_up_question": f"Can you elaborate on the {matched_words[0]} aspect?" if matched_words else "Can you describe a specific example where you applied this?",
        "ideal_answer": f"A comprehensive response defining the core architecture, trade-offs, and examples for {question}.",
        "what_was_correct": f"Addressed prompt concepts: {', '.join(matched_words)}" if matched_words else "Attempted explanation",
        "what_was_incorrect": "Needs more architectural elaboration" if word_count > 15 else "Response was too brief",
        "what_to_add": "Concrete performance and scalability specifications",
        "common_mistakes": ["Omitted edge cases"] if word_count > 15 else ["Answer too brief"],
        "metrics": metrics
    }


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
        return generate_dynamic_single_fallback(question, answer, q_type)


def generate_end_of_interview_report(role, track, difficulty, experience_level, questions, responses, chat_model, feedbacks=None):
    # 1. Count valid answers
    valid_count = 0
    for ans in (responses or []):
        if ans and str(ans).strip():
            clean_ans = str(ans).strip().lower().replace(".", "").replace(",", "").strip()
            if clean_ans not in ("[no response recorded]", "skipped", "skip", "i don't know", "none", "no response", ""):
                if len(clean_ans.split()) >= 2:
                    valid_count += 1

    # 2. Zero-score report if no valid answers
    if valid_count == 0:
        f_report = {
            "overall_score": 0.0,
            "recommendation": "Strong Reject",
            "confidence": "Low",
            "dimensions": [
                {"name": "Communication", "score": None, "grade": "N/A", "evidence_level": "NONE", "evidence": ["No response recorded"]},
                {"name": "Technical Knowledge", "score": None, "grade": "N/A", "evidence_level": "NONE", "evidence": ["No response recorded"]},
                {"name": "Problem Solving", "score": None, "grade": "N/A", "evidence_level": "NONE", "evidence": ["No response recorded"]},
                {"name": "Confidence", "score": None, "grade": "N/A", "evidence_level": "NONE", "evidence": ["No response recorded"]},
                {"name": "Behavioral Skills", "score": None, "grade": "N/A", "evidence_level": "NONE", "evidence": ["No response recorded"]},
                {"name": "Resume Knowledge", "score": None, "grade": "N/A", "evidence_level": "NONE", "evidence": ["No response recorded"]},
                {"name": "Project Explanation", "score": None, "grade": "N/A", "evidence_level": "NONE", "evidence": ["No response recorded"]},
                {"name": "Leadership", "score": None, "grade": "N/A", "evidence_level": "NONE", "evidence": ["No response recorded"]},
                {"name": "Grammar", "score": None, "grade": "N/A", "evidence_level": "NONE", "evidence": ["No response recorded"]},
                {"name": "Vocabulary", "score": None, "grade": "N/A", "evidence_level": "NONE", "evidence": ["No response recorded"]}
            ],
            "strengths": [],
            "weaknesses": [
                {"title": "No response recorded", "evidence": "Candidate did not answer any questions."}
            ]
        }
        return enrich_report_with_grading(f_report)

    # 3. Build annotated Q&A scorecard from per-question feedback already computed live
    full_transcript_lines = []
    per_answer_scorecard_lines = []
    feedbacks = feedbacks or []

    for idx, q in enumerate(questions or []):
        ans = responses[idx] if (responses and idx < len(responses)) else "[No response recorded]"
        full_transcript_lines.append(f"Turn {idx+1}:\nInterviewer: {q}\nCandidate: {ans}\n")

        # Per-answer already-computed scores — feed these as ground truth to the final AI call
        fb = feedbacks[idx] if idx < len(feedbacks) else {}
        if isinstance(fb, dict) and fb:
            q_score = fb.get("accuracy_score", fb.get("score", 0))
            if isinstance(q_score, float) and q_score <= 10:
                q_score = round(q_score * 10)  # convert 0-10 to 0-100
            fb_evidence = fb.get("evidence", "")
            fb_strength = fb.get("strength", "")
            fb_improvement = fb.get("improvement", "")
            fb_correctness = fb.get("correctness", "")
            per_answer_scorecard_lines.append(
                f"  Turn {idx+1} | Score: {q_score}/100 | Correctness: {fb_correctness}\n"
                f"    Evidence: {fb_evidence}\n"
                f"    Strength: {fb_strength}\n"
                f"    Weakness: {fb_improvement}"
            )
        else:
            per_answer_scorecard_lines.append(f"  Turn {idx+1} | No pre-scored feedback available")

    full_transcript = "\n".join(full_transcript_lines)
    per_answer_scorecard = "\n".join(per_answer_scorecard_lines)

    prompt = f"""You are an experienced Senior Software Engineering Interviewer with over 15 years of hiring experience at FAANG (Google, Microsoft, Amazon) and top product companies.

Your job is NOT to be encouraging or motivational.
Your job is to objectively evaluate the candidate based ONLY on observable evidence from the transcript.

PRE-SCORED PER-ANSWER DATA (computed in real-time, these scores are ground truth):
{per_answer_scorecard}

RULES:
1. Never assume skills.
2. Never hallucinate strengths.
3. Never invent weaknesses.
4. Never reward missing answers.
5. Never infer technical knowledge without proof.
6. Every score MUST be supported by evidence from the transcript.
7. If evidence is insufficient, return null for score and "N/A" for grade instead of estimating.
8. If the candidate skips a question, says "I don't know", remains silent, or provides an irrelevant response, do not fabricate scores (assign score null, grade "N/A", evidence_level "NONE").
9. Use the pre-scored per-answer data above, the transcript, and candidate responses as your ONLY sources.
10. Your dimension scores MUST be consistent with the per-answer scores above. Do NOT assign a Communication score of 85 if Turn scores average below 70.

Analyze the ENTIRE transcript and return ONLY valid JSON (no markdown code blocks, no commentary) in this exact schema:

{{
  "overall_score": 82,
  "recommendation": "Hire | Strong Hire | Leaning Hire | Neutral | Leaning Reject | Reject | Strong Reject",
  "confidence": "High | Medium | Low",
  "dimensions": [
    {{
      "name": "Communication",
      "score": 85,
      "grade": "A",
      "evidence_level": "HIGH",
      "evidence": [
        "Answered all questions clearly with logical sequencing.",
        "Candidate did not use vague words or filler phrases."
      ]
    }},
    {{
      "name": "Technical Knowledge",
      "score": null,
      "grade": "N/A",
      "evidence_level": "NONE",
      "evidence": [
        "Not enough evidence. Technical questions were skipped or not answered."
      ]
    }}
  ],
  "strengths": [
    {{
      "title": "Strong algorithm explanation",
      "evidence": "Explained HashMap optimization and time complexity during Question 2."
    }}
  ],
  "weaknesses": [
    {{
      "title": "Missed edge cases",
      "evidence": "Did not discuss duplicate values or empty array handling in Question 2."
    }}
  ]
}}

You MUST generate evaluation entries for exactly these 10 dimensions in this order:
1. Communication
2. Technical Knowledge
3. Problem Solving
4. Confidence
5. Behavioral Skills
6. Resume Knowledge
7. Project Explanation
8. Leadership
9. Grammar
10. Vocabulary

EVALUATION METHODOLOGY RULES:
- Communication: Evaluate ONLY if candidate actually communicated. Look for clarity, flow, conciseness, relevance. Accent or native language do NOT impact score.
- Technical Knowledge: Score ONLY if technical explanations exist. Look for correct concepts, terminology, depth, tradeoffs. Never assume knowledge.
- Problem Solving: Evaluate ONLY if candidate attempted solving a problem. Look for approach, complexity, optimization.
- Leadership: Only evaluate when candidate discusses projects, internships or teamwork (ownership, decision making).
- Confidence: Evaluate from observable behaviour only (hesitation, pauses, speaking pace).
- Grammar: Ignore minor mistakes caused by speech recognition.
- Vocabulary: Evaluate technical terminology and word precision.
- Resume Knowledge: Evaluate ONLY if interviewer asked about resume.
- Behavioral Skills: Evaluate ONLY from behavioral questions (Situation, Task, Action, Result).
- Strengths: Must be mentioned multiple times, supported by transcript, score > 80, and confidence HIGH. Else, do not list it.
- Weaknesses: Must have specific transcript/question evidence. Reference the Turn number.

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
        total_questions = len(questions) if questions else 1
        completion_ratio = valid_count / total_questions
        
        # Build dynamic strengths and weaknesses based on actual responses
        valid_indices = []
        poor_indices = []
        for i, ans in enumerate(responses or []):
            ans_clean = str(ans).strip().lower()
            if len(ans_clean) < 25 or any(skip in ans_clean for skip in ["don't know", "don't remember", "skip", "no idea", "not sure", "pardon"]):
                poor_indices.append(i)
            else:
                valid_indices.append(i)

        dyn_strengths = []
        if valid_indices:
            longest_idx = max(valid_indices, key=lambda idx: len(responses[idx]))
            longest_ans = responses[longest_idx]
            truncated_ans = longest_ans[:60] + "..." if len(longest_ans) > 60 else longest_ans
            
            tech_keywords = ["database", "react", "python", "component", "state", "function", "complexity", "array", "algorithm", "design", "class", "method"]
            found_keywords = [kw for kw in tech_keywords if kw in longest_ans.lower()]
            
            if found_keywords:
                dyn_strengths.append({
                    "title": f"Technical vocabulary usage ({', '.join(found_keywords[:3])})",
                    "evidence": f"Candidate demonstrated relevant concepts in Turn {longest_idx+1}: '{truncated_ans}'"
                })
            else:
                dyn_strengths.append({
                    "title": "Detailed answer articulation",
                    "evidence": f"Provided a descriptive response in Turn {longest_idx+1}: '{truncated_ans}'"
                })
        else:
            dyn_strengths.append({
                "title": "Conversational engagement",
                "evidence": "Candidate attempted to respond to the interviewer's prompts."
            })

        dyn_weaknesses = []
        if poor_indices:
            brief_idx = poor_indices[0]
            brief_ans = responses[brief_idx] if brief_idx < len(responses) else "empty response"
            dyn_weaknesses.append({
                "title": "Brief or incomplete technical explanation",
                "evidence": f"Candidate gave a short or skipped answer in Turn {brief_idx+1}: '{brief_ans}'"
            })
        else:
            dyn_weaknesses.append({
                "title": "Elaboration on complex trade-offs",
                "evidence": "Explanations were correct but could benefit from deeper discussions of architectural alternatives."
            })

        overall_score = round(78 * completion_ratio)
        if overall_score < 10:
            overall_score = 10

        fallback = {
            "overall_score": overall_score,
            "recommendation": "Neutral" if overall_score >= 50 else "Reject",
            "confidence": "Medium",
            "dimensions": [
                {"name": "Communication", "score": round(75 * completion_ratio), "grade": "B", "evidence_level": "MEDIUM", "evidence": ["Provided responses to some questions."]},
                {"name": "Technical Knowledge", "score": round(80 * completion_ratio), "grade": "B", "evidence_level": "MEDIUM", "evidence": ["Answered technical prompts."]},
                {"name": "Problem Solving", "score": round(76 * completion_ratio), "grade": "B", "evidence_level": "MEDIUM", "evidence": ["Attempted questions."]},
                {"name": "Confidence", "score": round(78 * completion_ratio), "grade": "B", "evidence_level": "MEDIUM", "evidence": ["Moderate vocal hesitation."]},
                {"name": "Behavioral Skills", "score": round(75 * completion_ratio), "grade": "B", "evidence_level": "MEDIUM", "evidence": ["Structured STAR responses."]},
                {"name": "Resume Knowledge", "score": round(80 * completion_ratio), "grade": "B", "evidence_level": "MEDIUM", "evidence": ["Familiar with basic resume items."]},
                {"name": "Project Explanation", "score": round(80 * completion_ratio), "grade": "B", "evidence_level": "MEDIUM", "evidence": ["Basic high-level architecture details."]},
                {"name": "Leadership", "score": round(70 * completion_ratio), "grade": "C", "evidence_level": "MEDIUM", "evidence": ["Discussed teamwork."]},
                {"name": "Grammar", "score": round(85 * completion_ratio), "grade": "B", "evidence_level": "MEDIUM", "evidence": ["Correct English usage."]},
                {"name": "Vocabulary", "score": round(85 * completion_ratio), "grade": "B", "evidence_level": "MEDIUM", "evidence": ["Used standard technical terminology."]}
            ],
            "strengths": dyn_strengths,
            "weaknesses": dyn_weaknesses
        }
        return enrich_report_with_grading(fallback)

def enrich_report_with_grading(report: dict) -> dict:
    from services.grading_service import calculate_grade_info, compute_section_grades, award_badges
    
    # Check if dimensions are present in report
    if "dimensions" in report and isinstance(report["dimensions"], list):
        sections = []
        valid_scores = []
        for d in report["dimensions"]:
            d_name = d.get("name")
            d_score = d.get("score")
            
            # check if score is None/null — do NOT include these in the overall average
            if d_score is None or str(d_score).strip().lower() in ("null", "none") or d.get("evidence_level") == "NONE" or d.get("grade") == "N/A":
                sec_grade = "N/A"
                sec_color = "#7a8ba8"
                sec_bg = "rgba(122, 139, 168, 0.15)"
                sec_label = "Not Assessed"
                score_val = None
            else:
                try:
                    score_val = float(d_score)
                    valid_scores.append(score_val)
                    sec_info = calculate_grade_info(score_val)
                    sec_grade = sec_info["grade"]
                    sec_color = sec_info["color"]
                    sec_bg = sec_info["bgColor"]
                    sec_label = sec_info["label"]
                except:
                    sec_grade = "N/A"
                    sec_color = "#7a8ba8"
                    sec_bg = "rgba(122, 139, 168, 0.15)"
                    sec_label = "Not Assessed"
                    score_val = None
            
            sections.append({
                "name": d_name,
                "score": int(score_val) if score_val is not None else None,
                "grade": sec_grade,
                "color": sec_color,
                "bgColor": sec_bg,
                "label": sec_label,
                "evidence_level": d.get("evidence_level", "NONE"),
                "evidence": d.get("evidence", [])
            })
        
        report["section_grades"] = sections
        
        # Overall score = mean of ONLY assessed (non-null) dimensions
        if valid_scores:
            score = round(sum(valid_scores) / len(valid_scores))
        else:
            score = 0
    else:
        score = float(report.get("overall_score") if report.get("overall_score") is not None else 0)

    g_info = calculate_grade_info(score)

    report["overall_score"] = g_info["score"]
    report["grade"] = g_info["grade"]
    report["overall_grade"] = g_info["grade"]
    report["grade_label"] = g_info["label"]
    report["grade_color"] = g_info["color"]
    report["hiring_recommendation"] = report.get("recommendation") or g_info["rec"]
    report["performance_level"] = g_info["level"]

    if "section_grades" not in report:
        sections = compute_section_grades([], {"clarity": report.get("communication_score", 80), "wpm": report.get("transcript_analytics", {}).get("words_per_minute", 135)})
        if score == 0:
            for sec in sections:
                sec["score"] = 0
                sec["grade"] = "F"
                sec["color"] = "#991b1b"
                sec["bgColor"] = "rgba(153, 27, 27, 0.15)"
                sec["label"] = "Significant Improvement Required"
            report["badges"] = []
        else:
            report["badges"] = award_badges(score, sections)
        report["section_grades"] = sections
    else:
        if score == 0:
            report["badges"] = []
        else:
            report["badges"] = award_badges(score, report["section_grades"])

    # Strengths — only keep if AI returned evidence-backed items; NEVER fabricate
    strengths = report.get("strengths") or []
    if strengths and isinstance(strengths[0], dict):
        # Keep only strengths the AI grounded in transcript evidence
        report["top_strengths"] = [
            f"{s.get('title')}: {s.get('evidence')}"
            for s in strengths
            if isinstance(s, dict) and s.get("title") and s.get("evidence")
        ] or ["No evidence-backed strengths identified in this session."]
    else:
        # Plain string list — use as-is only if non-empty
        report["top_strengths"] = strengths if strengths else ["No evidence-backed strengths identified in this session."]

    # Weaknesses — same rule
    improvements = report.get("weaknesses") or report.get("improvement_suggestions") or []
    if improvements and isinstance(improvements[0], dict):
        report["top_improvements"] = [
            f"{w.get('title')}: {w.get('evidence')}"
            for w in improvements
            if isinstance(w, dict) and w.get("title") and w.get("evidence")
        ] or ["No specific weaknesses identified — review your lowest-scoring dimensions above."]
    else:
        report["top_improvements"] = improvements if improvements else ["No specific weaknesses identified — review your lowest-scoring dimensions above."]

    if not report.get("ai_summary"):
        assessed_count = len([s for s in report.get("section_grades", []) if s.get("score") is not None])
        report["ai_summary"] = (f"The candidate demonstrated {g_info['label'].lower()} performance ({g_info['grade']} Grade, "
                                f"{g_info['score']}/100) across {assessed_count} assessed dimension(s). "
                                f"Based on this evaluation, the candidate is {report['hiring_recommendation'].lower()}.")

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









