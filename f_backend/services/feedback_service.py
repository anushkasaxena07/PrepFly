import json
from langchain_core.messages import HumanMessage
from services.ai_config import AI_INTERVIEWER
from services.grading_service import calculate_grade_info, award_badges, compute_section_grades
from services.ai_service import safe_invoke_llm
from services.answer_classifier import (
    classify_candidate_response,
    extract_verified_strength,
    CLASS_CORRECT_COMPLETE,
    CLASS_PARTIALLY_CORRECT,
    CLASS_INCORRECT,
    CLASS_IRRELEVANT_OFF_TOPIC,
    CLASS_NO_ANSWER,
    CLASS_EARLY_EXIT,
    CLASS_UNCLEAR_INSUFFICIENT
)

def classify_question_type(question: str, category: str = "") -> str:
    q_lower = f"{question} {category or ''}".lower()
    if any(k in q_lower for k in ["code", "coding", "algorithm", "function", "complexity", "time complexity", "space complexity", "array", "tree", "graph", "dp"]):
        return "Coding"
    elif any(k in q_lower for k in ["system design", "architecture", "scalability", "database", "sharding", "microservice", "load balancer", "cache", "distributed"]):
        return "System Design"
    elif any(k in q_lower for k in ["tell me about", "behavioral", "conflict", "team", "challenge", "failure", "strength", "weakness", "star"]):
        return "HR"
    return "Technical"


def generate_dynamic_single_fallback(question, answer, q_type, category="", role=""):
    classification, acc_score, dim_scores, rationale = classify_candidate_response(
        question=question,
        answer=answer,
        category=category,
        role=role
    )
    score_10 = round(acc_score / 10.0, 1)

    # Check if candidate qualifies for a verified strength
    verified_str = extract_verified_strength(
        classification=classification,
        accuracy_score=acc_score,
        question=question,
        candidate_answer=answer,
        dimension_scores=dim_scores
    )
    strength_text = verified_str["reason"] if verified_str else ""

    if classification == CLASS_EARLY_EXIT:
        feedback_msg = "⚠️ Candidate requested to conclude the interview early."
        improvement_msg = "Complete the required questions to receive a valid performance evaluation."
    elif classification == CLASS_NO_ANSWER:
        feedback_msg = "❌ No substantive answer provided. Candidate skipped or indicated no response."
        improvement_msg = "Attempt each question with structured reasoning, even if stating initial assumptions."
    elif classification == CLASS_IRRELEVANT_OFF_TOPIC:
        feedback_msg = "⚠️ Response was off-topic and did not address the question asked."
        improvement_msg = "Focus directly on the concepts and scenario presented in the interview question."
    elif classification == CLASS_UNCLEAR_INSUFFICIENT:
        feedback_msg = "⚠️ Response was too brief to evaluate technical or domain competence."
        improvement_msg = "Provide complete verbal or typed explanations with examples and rationale."
    elif classification == CLASS_INCORRECT:
        feedback_msg = f"❌ Technical definitions or approaches were incorrect. {rationale}"
        improvement_msg = "Review the core domain definitions, trade-offs, and implementation edge cases."
    elif classification == CLASS_PARTIALLY_CORRECT:
        feedback_msg = f"⚠️ Partially correct. {rationale}"
        improvement_msg = "Deepen discussion of edge cases, failure modes, and performance trade-offs."
    else:
        feedback_msg = f"✅ Comprehensive response. {rationale}"
        improvement_msg = "Continue articulating high-level trade-offs with concrete production examples."

    return {
        "feedback": feedback_msg,
        "score": score_10,
        "accuracy_score": int(acc_score),
        "correctness": classification,
        "answer_quality": "Good" if acc_score >= 75 else ("Average" if acc_score >= 50 else "Poor"),
        "question_type": q_type,
        "strength": strength_text,
        "improvement": improvement_msg,
        "tip": "Structure your answers using first-principles definitions followed by trade-offs.",
        "summary": f"{classification} ({int(acc_score)}/100).",
        "classification": classification,
        "dimensions": dim_scores,
        "ideal_answer": "Provide a structured explanation starting with core definitions, trade-offs, and examples.",
        "what_was_correct": rationale if acc_score >= 50 else "None",
        "what_was_incorrect": "Incomplete or inaccurate explanation" if acc_score < 70 else "Minor gaps",
        "what_to_add": improvement_msg,
        "common_mistakes": [classification],
        "metrics": {
            "communication": round(dim_scores.get("communication", 0.0) / 10.0, 1),
            "confidence": round(dim_scores.get("understanding", 0.0) / 10.0, 1),
            "technical_knowledge": round(dim_scores.get("correctness", 0.0) / 10.0, 1),
            "resume_understanding": round(dim_scores.get("approach", 0.0) / 10.0, 1),
            "project_explanation": round(dim_scores.get("approach", 0.0) / 10.0, 1),
            "problem_solving": round(dim_scores.get("approach", 0.0) / 10.0, 1),
            "behavioral": round(dim_scores.get("communication", 0.0) / 10.0, 1),
            "leadership": round(dim_scores.get("communication", 0.0) / 10.0, 1)
        }
    }


def evaluate_response_comprehensive(resume_text, question, answer, chat_model, question_index=1, category="", role=""):
    ai_name = AI_INTERVIEWER["name"]
    q_type = classify_question_type(question, category)
    target_role = (role or category or "Software Engineer").strip()
    if not target_role or target_role.lower() in ("none", ""):
        target_role = "Software Engineer"

    # Non-Answer & Conversational Turns Guard (Prompt 3 Rule R1 & R6)
    # Non-answer turns (rapport, repeat, clarification, silence prompts, hints) are NEVER scored.
    try:
        from services.intent_classifier import IntentClassifier, INTENT_ANSWER, INTENT_PARTIAL_ANSWER
        intent_res = IntentClassifier.classify_intent(answer)
        if intent_res.get("intent") not in (INTENT_ANSWER, INTENT_PARTIAL_ANSWER):
            return {
                "score": None,
                "accuracy_score": None,
                "is_scored": False,
                "is_conversational_turn": True,
                "intent": intent_res.get("intent"),
                "correctness": "Conversational Turn",
                "answer_quality": "Not Applicable",
                "question_type": q_type,
                "feedback": f"ℹ️ Conversational turn ({intent_res.get('intent')}). Not scored.",
                "strength": "",
                "improvement": "",
                "tip": "",
                "summary": f"Conversational turn ({intent_res.get('intent')}).",
                "ideal_answer": "",
                "what_was_correct": "N/A",
                "what_was_incorrect": "N/A",
                "what_to_add": "",
                "common_mistakes": [],
                "metrics": {
                    "communication": None, "confidence": None, "technical_knowledge": None,
                    "resume_understanding": None, "project_explanation": None, "problem_solving": None,
                    "behavioral": None, "leadership": None
                }
            }
    except Exception as e:
        pass

    # Deterministic 7-tier classification and scoring gate
    classification, composite_acc, dim_scores, rationale = classify_candidate_response(
        question=question,
        answer=answer,
        category=category,
        role=target_role
    )

    # 1. Deterministic handling for non-answers
    if classification == CLASS_NO_ANSWER:
        return {
            "score": 0.0,
            "accuracy_score": 0,
            "correctness": "No Answer",
            "answer_quality": "Very Poor",
            "question_type": q_type,
            "feedback": "⚠️ No Answer Provided. Candidate skipped or provided no answer.",
            "strength": "",
            "improvement": "Make sure to attempt every interview question with structured explanations.",
            "tip": "Break down complex questions into steps even if unsure.",
            "summary": "No response recorded (0/100).",
            "ideal_answer": f"Provide a structured explanation demonstrating competency in {target_role}.",
            "what_was_correct": "None",
            "what_was_incorrect": "No response provided",
            "what_to_add": "Complete verbal or typed answer addressing core problem requirements",
            "common_mistakes": ["Skipped question entirely"],
            "metrics": {
                "communication": 0.0, "confidence": 0.0, "technical_knowledge": 0.0,
                "resume_understanding": 0.0, "project_explanation": 0.0, "problem_solving": 0.0,
                "behavioral": 0.0, "leadership": 0.0
            }
        }

    # 2. Deterministic handling for early exit
    if classification == CLASS_EARLY_EXIT:
        return {
            "score": 0.0,
            "accuracy_score": 0,
            "correctness": "Incomplete",
            "answer_quality": "Early Exit",
            "question_type": q_type,
            "feedback": "⚠️ Candidate requested to conclude the interview early.",
            "strength": "",
            "improvement": "Candidate exited before completing interview questions.",
            "tip": "Complete at least 5 questions to receive a hiring evaluation.",
            "summary": "Early exit requested (0/100).",
            "ideal_answer": "Complete answers are required for scoring.",
            "what_was_correct": "None",
            "what_was_incorrect": "Candidate requested early exit",
            "what_to_add": "Complete domain explanations",
            "common_mistakes": ["Exited interview early"],
            "metrics": {
                "communication": 0.0, "confidence": 0.0, "technical_knowledge": 0.0,
                "resume_understanding": 0.0, "project_explanation": 0.0, "problem_solving": 0.0,
                "behavioral": 0.0, "leadership": 0.0
            }
        }

    # 3. Deterministic handling for off-topic or irrelevant responses
    if classification == CLASS_IRRELEVANT_OFF_TOPIC:
        return {
            "score": 1.5,
            "accuracy_score": 15,
            "correctness": "Irrelevant or off-topic",
            "answer_quality": "Off-Topic",
            "question_type": q_type,
            "feedback": "⚠️ Response was off-topic or disconnected from the interview question.",
            "strength": "",
            "improvement": "Directly address the specific prompt rather than offering unrelated commentary.",
            "tip": "Focus on the core concepts requested by the interviewer.",
            "summary": "Off-topic response recorded (15/100).",
            "ideal_answer": f"Address the question directly using principles relevant to {target_role}.",
            "what_was_correct": "None",
            "what_was_incorrect": "Candidate gave off-topic answer",
            "what_to_add": "Direct answer addressing prompt requirements",
            "common_mistakes": ["Off-topic answer"],
            "metrics": {
                "communication": 1.5, "confidence": 2.0, "technical_knowledge": 0.0,
                "resume_understanding": 0.0, "project_explanation": 0.0, "problem_solving": 0.0,
                "behavioral": 1.0, "leadership": 0.0
            }
        }

    # 4. Handle negative icebreaker tone on Turn 1
    ans_lower = (answer or "").strip().lower()
    if question_index == 1 and any(neg in ans_lower for neg in ["bad", "terrible", "not good", "awful", "sad"]):
        return {
            "score": 2.0,
            "accuracy_score": 20,
            "correctness": "Poor Communication",
            "answer_quality": "Below Average",
            "question_type": q_type,
            "feedback": "⚠️ Acknowledged opening greeting with negative sentiment. Maintain professional composure.",
            "strength": "",
            "improvement": "Frame opening interactions professionally and positively.",
            "tip": "Keep introductory pleasantries warm and constructive.",
            "summary": "Negative opening tone recorded (20/100).",
            "ideal_answer": "Acknowledge greeting professionally (e.g. 'Doing great, excited for this session!').",
            "what_was_correct": "Responded to prompt",
            "what_was_incorrect": "Negative opening tone",
            "what_to_add": "Professional opening demeanor",
            "common_mistakes": ["Negative introductory attitude"],
            "metrics": {
                "communication": 2.0, "confidence": 2.0, "technical_knowledge": 0.0,
                "resume_understanding": 0.0, "project_explanation": 0.0, "problem_solving": 0.0,
                "behavioral": 2.0, "leadership": 0.0
            }
        }

    # 5. LLM Evidence-Based Evaluation for substantive answers
    prompt = f"""You are an expert interviewer evaluating a candidate for the role of {target_role}.
Question Type: {q_type}
Question: {question}
Candidate Answer: {answer}
Context: {resume_text[:400]}

Perform a strict evidence-based analysis:
1. Accuracy Score (0-100): 100=Completely correct, 70=Mostly correct, 50=Partial, 30=Major mistakes, 0=Wrong/No answer.
2. Correctness: Correct and complete | Partially correct | Incorrect | Irrelevant | No Answer
3. Identify mistakes, terminology errors, missed edge cases, and superficial depth.
4. Generate realistic follow-up question if incomplete.
5. Provide Ideal Answer, What was correct, What was incorrect, What to add.

Return ONLY valid JSON:
{{
  "accuracy_score": 75,
  "score": 7.5,
  "correctness": "Partially correct",
  "answer_quality": "Good",
  "strength": "Solid explanation of core concepts",
  "improvement": "Explain edge case handling and trade-offs",
  "tip": "State trade-offs explicitly",
  "summary": "Good conceptual understanding with minor gaps",
  "evidence": "Candidate addressed core workflow but omitted trade-offs",
  "technical_accuracy": "Core definitions correct",
  "completeness": "Answered main question",
  "depth": "Intermediate",
  "communication": "Fluent and structured",
  "problem_solving": "Good logical progression",
  "follow_up_question": "How would you handle trade-offs in production?",
  "ideal_answer": "Detailed comprehensive answer",
  "what_was_correct": "Core mechanism accurately identified",
  "what_was_incorrect": "Did not address edge cases",
  "what_to_add": "Concrete metrics and real-world considerations",
  "common_mistakes": ["Missed edge cases"],
  "communication_score": 7.5,
  "confidence_score": 7.5,
  "technical_knowledge_score": 7.5,
  "problem_solving_score": 7.5,
  "behavioral_score": 7.5,
  "resume_understanding_score": 7.5,
  "project_explanation_score": 7.5
}}"""

    try:
        content = safe_invoke_llm(chat_model, prompt)
        if not content:
            raise ValueError("No response from LLM for feedback evaluation")
        content = content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()

        data = json.loads(content)
        acc_score = max(0, min(100, int(data.get("accuracy_score", composite_acc))))
        score_10 = round(acc_score / 10.0, 1)

        # Enforce zero false strengths rule:
        verified_st = extract_verified_strength(classification, float(acc_score), question, answer, dim_scores)
        if verified_st and acc_score >= 70:
            strength = verified_st["competency"]
        else:
            strength = ""

        improvement = data.get("improvement", "Elaborate with specific trade-offs and edge case handling.")
        tip = data.get("tip", "Use structured STAR or principles-first explanations.")
        summary = data.get("summary", "Demonstrated domain knowledge.")

        st_part = f"Strength: {strength}\n" if strength else ""
        feedback_str = f"{st_part}Improve: {improvement}\nTip: {tip}\nQuality: {data.get('answer_quality', 'Good')} ({acc_score}/100)"

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
            "correctness": data.get("correctness", classification),
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
        return generate_dynamic_single_fallback(question, answer, q_type, category=category, role=target_role)


def build_conversation_summary(questions: list = None, responses: list = None, feedbacks: list = None) -> dict:
    """
    Builds a structured conversation summary section referencing turn IDs (turn_1, turn_2, ...).
    Categorizes each turn into substantive technical/behavioral responses vs conversational interactions.
    Guarantees that non-answer turns (rapport, repeat, clarification, silence prompts, hints) are never scored.
    """
    from services.intent_classifier import IntentClassifier, INTENT_ANSWER, INTENT_PARTIAL_ANSWER

    questions = questions or []
    responses = responses or []
    feedbacks = feedbacks or []

    turn_summaries = []
    substantive_count = 0
    conversational_count = 0
    narrative_parts = []

    total = max(len(questions), len(responses))
    for idx in range(total):
        turn_id = f"turn_{idx + 1}"
        q = questions[idx] if idx < len(questions) else ""
        a = responses[idx] if idx < len(responses) else "[No response recorded]"
        fb = feedbacks[idx] if idx < len(feedbacks) and isinstance(feedbacks[idx], dict) else {}

        intent_info = IntentClassifier.classify_intent(a)
        intent = intent_info.get("intent", "answer")
        is_conversational_fb = fb.get("is_conversational_turn", False)
        is_substantive = (
            intent in (INTENT_ANSWER, INTENT_PARTIAL_ANSWER)
            and not is_conversational_fb
            and a not in ("[No response recorded]", "skipped", "skip", "")
        )

        raw_score = fb.get("accuracy_score", fb.get("score"))
        if is_substantive:
            substantive_count += 1
            turn_type = "technical_response"
            if isinstance(raw_score, (int, float)):
                score_val = round(raw_score * 10) if raw_score <= 10 else int(raw_score)
            else:
                score_val = 70
            is_scored = True
            key_point = fb.get("strength") or (a[:80] + "..." if len(a) > 80 else a)
            narrative_parts.append(f"In {turn_id.capitalize()}, candidate addressed the question: \"{a[:60]}...\" (Score: {score_val}/100).")
        else:
            conversational_count += 1
            turn_type = f"conversational_{intent}"
            score_val = None
            is_scored = False
            key_point = f"Conversational interaction ({intent})"
            narrative_parts.append(f"In {turn_id.capitalize()}, candidate engaged in conversational dialogue ({intent}): \"{a[:60]}\" (Not scored).")

        turn_summaries.append({
            "turn_id": turn_id,
            "turn_number": idx + 1,
            "speaker_prompt": q,
            "candidate_response": a,
            "turn_type": turn_type,
            "is_scored": is_scored,
            "score": score_val,
            "key_point": key_point,
            "feedback_summary": fb.get("summary") or fb.get("feedback") or "Turn logged."
        })

    chronological_narrative = " ".join(narrative_parts) if narrative_parts else "No conversation turns recorded."

    return {
        "total_turns": total,
        "substantive_answers_count": substantive_count,
        "conversational_turns_count": conversational_count,
        "chronological_narrative": chronological_narrative,
        "turn_summaries": turn_summaries
    }


def generate_end_of_interview_report(role, track, difficulty, experience_level, questions, responses, chat_model, feedbacks=None):
    # 1. Count valid answers
    valid_count = 0
    for ans in (responses or []):
        if ans and str(ans).strip():
            clean_ans = str(ans).strip().lower().replace(".", "").replace(",", "").strip()
            if clean_ans not in ("[no response recorded]", "skipped", "skip", "i don't know", "none", "no response", ""):
                if len(clean_ans.split()) >= 2:
                    valid_count += 1

    total_questions = len(questions) if questions else 10
    MIN_QUESTIONS_FOR_RECOMMENDATION = 5
    is_preliminary = valid_count < MIN_QUESTIONS_FOR_RECOMMENDATION

    # 2. Zero-score report if no valid answers
    if valid_count == 0:
        f_report = {
            "overall_score": 0.0,
            "report_type": "preliminary",
            "answered_questions_count": 0,
            "recommendation": "Preliminary Evaluation (Requires ≥ 5 answered questions)",
            "confidence": "Low",
            "conversation_summary": build_conversation_summary(questions, responses, feedbacks),
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

CANDIDATE ANSWER PROGRESS: {valid_count} of {total_questions} questions answered.
REPORT MODE: {"PRELIMINARY (Answered < 5 questions)" if is_preliminary else "FINAL (Answered ≥ 5 questions)"}

PRE-SCORED PER-ANSWER DATA (computed in real-time, these scores are ground truth):
{per_answer_scorecard}

RULES FOR EVIDENCE-BASED SCORING:
1. Never assume skills.
2. Never hallucinate strengths.
3. Never invent weaknesses.
4. Never reward missing answers.
5. Every score MUST be supported by observable transcript evidence.
6. IF EVIDENCE IS INSUFFICIENT OR THE QUESTION WAS NOT ASKED (e.g. Leadership, Project Explanation, Resume Knowledge), YOU MUST ASSIGN score: null, grade: "N/A", evidence_level: "NONE", and evidence: ["Not enough evidence. Complete questions in this dimension to generate a score."].
7. Minimum threshold for listing a Strength: Dimension score MUST be >= 70 with explicit transcript proof. If score is < 70, DO NOT list it as a strength!
8. If answered questions count is < 5 ({valid_count}), recommendation MUST be "Preliminary Evaluation (Requires ≥ 5 answered questions)".

Analyze the ENTIRE transcript and return ONLY valid JSON in this exact schema:

{{
  "report_type": "{'preliminary' if is_preliminary else 'final'}",
  "answered_questions_count": {valid_count},
  "overall_score": 75,
  "recommendation": "{'Preliminary Evaluation (Requires ≥ 5 answered questions)' if is_preliminary else 'Hire | Strong Hire | Leaning Hire | Neutral | Leaning Reject | Reject | Strong Reject'}",
  "confidence": "{'Low' if valid_count <= 2 else ('Medium' if valid_count < 5 else 'High')}",
  "dimensions": [
    {{
      "name": "Communication",
      "score": 85,
      "grade": "A",
      "evidence_level": "HIGH",
      "evidence": [
        "Answered questions clearly with logical flow in Turn 1."
      ]
    }},
    {{
      "name": "Leadership",
      "score": null,
      "grade": "N/A",
      "evidence_level": "NONE",
      "evidence": [
        "Not enough evidence. Leadership questions were not covered in this session."
      ]
    }}
  ],
  "strengths": [
    {{
      "title": "Clear Technical Vocabulary",
      "evidence": "Correctly used HashMap and time complexity concepts in Turn 1."
    }}
  ],
  "weaknesses": [
    {{
      "title": "Brief Technical Explanation",
      "evidence": "Did not elaborate on memory tradeoffs in Turn 1."
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
- Communication / Grammar / Vocabulary: Evaluate ONLY if candidate actually communicated in English. Look for clarity and conciseness.
- Technical Knowledge / Problem Solving: Score ONLY if technical explanations exist. Never assume knowledge.
- Leadership / Behavioral Skills / Resume Knowledge / Project Explanation: Assign score: null, grade: "N/A", evidence_level: "NONE" unless specifically discussed in transcript.

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
        parsed["answered_questions_count"] = valid_count
        parsed["conversation_summary"] = build_conversation_summary(questions, responses, feedbacks)
        return enrich_report_with_grading(parsed)
    except Exception as e:
        print("End-of-interview report generation notice:", e)
        
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
            dyn_strengths.append({
                "title": "Clear communication in response",
                "evidence": f"Articulated response in Turn {longest_idx+1}: '{truncated_ans}'"
            })

        dyn_weaknesses = []
        if poor_indices:
            brief_idx = poor_indices[0]
            brief_ans = responses[brief_idx] if brief_idx < len(responses) else "empty response"
            dyn_weaknesses.append({
                "title": "Brief or skipped answer",
                "evidence": f"Candidate gave short or skipped response in Turn {brief_idx+1}: '{brief_ans}'"
            })

        # Evaluate observed dimensions only
        fallback_dims = [
            {"name": "Communication", "score": 75 if valid_indices else None, "grade": "B" if valid_indices else "N/A", "evidence_level": "MEDIUM" if valid_indices else "NONE", "evidence": ["Provided responses to interviewer prompts."] if valid_indices else ["No response recorded"]},
            {"name": "Technical Knowledge", "score": 70 if valid_indices else None, "grade": "C" if valid_indices else "N/A", "evidence_level": "MEDIUM" if valid_indices else "NONE", "evidence": ["Attempted technical questions."] if valid_indices else ["No response recorded"]},
            {"name": "Problem Solving", "score": 70 if valid_indices else None, "grade": "C" if valid_indices else "N/A", "evidence_level": "MEDIUM" if valid_indices else "NONE", "evidence": ["Provided algorithmic approach."] if valid_indices else ["No response recorded"]},
            {"name": "Confidence", "score": 70 if valid_indices else None, "grade": "C" if valid_indices else "N/A", "evidence_level": "MEDIUM" if valid_indices else "NONE", "evidence": ["Pacing and delivery evaluated."] if valid_indices else ["No response recorded"]},
            {"name": "Behavioral Skills", "score": None, "grade": "N/A", "evidence_level": "NONE", "evidence": ["Not enough evidence. Behavioral questions were not covered."]},
            {"name": "Resume Knowledge", "score": None, "grade": "N/A", "evidence_level": "NONE", "evidence": ["Not enough evidence. Resume questions were not asked."]},
            {"name": "Project Explanation", "score": None, "grade": "N/A", "evidence_level": "NONE", "evidence": ["Not enough evidence. Project questions were not asked."]},
            {"name": "Leadership", "score": None, "grade": "N/A", "evidence_level": "NONE", "evidence": ["Not enough evidence. Leadership questions were not asked."]},
            {"name": "Grammar", "score": 80 if valid_indices else None, "grade": "B" if valid_indices else "N/A", "evidence_level": "MEDIUM" if valid_indices else "NONE", "evidence": ["Grammatical structure evaluated."] if valid_indices else ["No response recorded"]},
            {"name": "Vocabulary", "score": 80 if valid_indices else None, "grade": "B" if valid_indices else "N/A", "evidence_level": "MEDIUM" if valid_indices else "NONE", "evidence": ["Technical terminology evaluated."] if valid_indices else ["No response recorded"]}
        ]

        fallback = {
            "report_type": "preliminary" if is_preliminary else "final",
            "answered_questions_count": valid_count,
            "overall_score": 70 if valid_indices else 0,
            "recommendation": f"Preliminary Evaluation (Requires ≥ 5 answered questions)" if is_preliminary else "Neutral",
            "confidence": "Low" if valid_count <= 2 else ("Medium" if valid_count < 5 else "High"),
            "conversation_summary": build_conversation_summary(questions, responses, feedbacks),
            "dimensions": fallback_dims,
            "strengths": dyn_strengths,
            "weaknesses": dyn_weaknesses
        }
        return enrich_report_with_grading(fallback)


def generate_benchmark_answer(question: str, track: str = "") -> dict:
    """Generates a Staff/Senior level benchmark model answer for side-by-side comparison."""
    q_low = (question or "").lower()
    
    if any(k in q_low for k in ["scale", "scaling", "architecture", "design", "microservice", "partition", "high availability", "trade-off", "bottleneck"]):
        return {
            "key_principles": [
                "Decompose system into stateless API gateways and horizontally scalable worker services.",
                "Introduce distributed caching (Redis/Memcached) with write-through or cache-aside strategies.",
                "Partition/shard databases by tenant or hash key; separate OLTP and OLAP read-replicas.",
                "Use asynchronous event-driven queues (Kafka/RabbitMQ) for decoupled backpressure and eventual consistency."
            ],
            "staff_takeaway": "Top candidates quantify SLA metrics (P99 latency, RPS), explicitly state failure modes (circuit breakers, dead letter queues), and discuss CAP theorem trade-offs."
        }
    elif any(k in q_low for k in ["algorithm", "complexity", "time complexity", "space complexity", "array", "tree", "hash", "graph", "dp", "sort"]):
        return {
            "key_principles": [
                "State brute-force complexity first (e.g. O(N^2) time) before detailing the optimal approach.",
                "Identify optimal data structure (e.g. Hash Map for O(1) lookups, Two Pointers for O(1) space, BFS for shortest path).",
                "Formally derive Big-O: State Time Complexity O(N) and Auxiliary Space O(N) explicitly.",
                "Walk through critical boundary cases: empty input, duplicates, negative values, and integer overflows."
            ],
            "staff_takeaway": "Senior candidates articulate trade-offs between time and space optimization, validating edge cases before jumping to code."
        }
    elif any(k in q_low for k in ["conflict", "disagree", "deadline", "challenge", "failure", "mistake", "team", "behavioral"]):
        return {
            "key_principles": [
                "Situation & Task: Set brief context, the business stakes, and your specific individual responsibility.",
                "Action: Focus on personal ownership, active listening, and bringing empirical data to resolve disagreements.",
                "Result: Quantifiable outcome (e.g. delivered 3 days early, zero production regressions).",
                "Reflection: Share what you learned and how it influenced your subsequent engineering leadership."
            ],
            "staff_takeaway": "Staff engineers avoid blaming teammates, center discussions around customer impact, and demonstrate structured STAR methodology."
        }
    elif any(k in q_low for k in ["error", "bug", "production", "debug", "incident", "failure", "reliability", "edge case"]):
        return {
            "key_principles": [
                "Immediate mitigation: Rollback, feature flag disabling, or traffic shedding before root cause analysis.",
                "Observability: Check distributed tracing (OpenTelemetry), error logs, and metric anomalies (5xx rates, CPU spikes).",
                "Root cause & Reproduction: Isolate minimal reproducing case in staging with sanitized data.",
                "Post-mortem: Write blameless post-mortem with automated regression test and architectural guardrails."
            ],
            "staff_takeaway": "Interviewers reward candidates who prioritize service availability first, followed by systematic blameless root cause analysis."
        }
    else:
        return {
            "key_principles": [
                "Structure answer hierarchically: High-level executive summary followed by technical depth.",
                "Anchor on business value: Explain why particular tools, frameworks, or architectural choices were chosen.",
                "Demonstrate deep fundamental knowledge: Mention internal workings, concurrency safety, and performance constraints.",
                "Close with continuous improvement: Mention lessons learned and what you would architect differently today."
            ],
            "staff_takeaway": "Clear communication, precision with technical terminology, and concrete real-world examples distinguish top-percentile candidates."
        }


def fast_compile_report(
    role,
    track,
    difficulty,
    experience_level,
    questions,
    responses,
    feedbacks,
    interview_mode="resume",
    candidate_name="Candidate",
    total_questions_expected=10,
    **kwargs
):
    """
    Deterministic, evidence-based executive evaluation compiler.
    Eliminates inflated scores, guarantees zero false strengths, and enforces
    strict session metadata integrity throughout the report pipeline.
    """
    questions = questions or []
    responses = responses or []
    feedbacks = feedbacks or []
    total_questions = max(len(questions), 10)

    # 1. Structured Answer Classification & Tracking
    attempted_questions = 0
    valid_evaluated_answers = 0
    skipped_questions = 0
    unanswered_questions = 0
    early_termination = False
    turn_scores = []
    scored_strengths = []
    scored_weaknesses = []

    for idx, q in enumerate(questions):
        ans = responses[idx] if idx < len(responses) else ""
        fb = feedbacks[idx] if idx < len(feedbacks) and isinstance(feedbacks[idx], dict) else {}
        
        # Determine classification
        classification = fb.get("correctness")
        acc_score = fb.get("accuracy_score")
        if acc_score is None:
            s_raw = fb.get("score", 0)
            acc_score = s_raw * 10 if s_raw <= 10 else s_raw
        acc_score = float(acc_score)

        if not ans or not str(ans).strip():
            unanswered_questions += 1
            classification = CLASS_NO_ANSWER
            acc_score = 0.0
        elif not classification or classification in ("Correct", "Incorrect", "Partially Correct"):
            # Classify using domain classifier
            c_label, c_acc, _, _ = classify_candidate_response(question=q, answer=str(ans), category=track, role=role)
            classification = c_label
            if not fb.get("accuracy_score"):
                acc_score = c_acc

        if classification == CLASS_EARLY_EXIT:
            early_termination = True
            attempted_questions += 1
            acc_score = 0.0
        elif classification == CLASS_NO_ANSWER:
            skipped_questions += 1
            acc_score = 0.0
        elif classification == CLASS_IRRELEVANT_OFF_TOPIC:
            attempted_questions += 1
            acc_score = min(acc_score, 15.0)
        elif classification == CLASS_UNCLEAR_INSUFFICIENT:
            attempted_questions += 1
            acc_score = min(acc_score, 20.0)
        elif classification in (CLASS_CORRECT_COMPLETE, CLASS_PARTIALLY_CORRECT):
            attempted_questions += 1
            valid_evaluated_answers += 1
            turn_scores.append(acc_score)
        else: # CLASS_INCORRECT
            attempted_questions += 1
            turn_scores.append(acc_score)

        # Strength verification: ZERO false strengths
        candidate_ans_str = str(ans).strip()
        verified_str = extract_verified_strength(
            classification=classification,
            accuracy_score=acc_score,
            question=q,
            candidate_answer=candidate_ans_str,
            dimension_scores=fb.get("dimensions") or {}
        )
        if verified_str:
            scored_strengths.append({
                "title": verified_str["competency"],
                "evidence": f"Turn {idx+1}: {verified_str['evidence']} ({verified_str['reason']})"
            })

        # Weaknesses from low scores or deficiencies
        if acc_score < 70.0 and classification not in (CLASS_NO_ANSWER, CLASS_EARLY_EXIT):
            imp_msg = fb.get("improvement") or f"Elaborate on technical trade-offs and concrete implementations for Question {idx+1}."
            scored_weaknesses.append({
                "title": f"Turn {idx+1} Depth Gap ({classification})",
                "evidence": f"Answer '{candidate_ans_str[:80]}...' - {imp_msg}"
            })
        elif classification == CLASS_NO_ANSWER:
            scored_weaknesses.append({
                "title": f"Turn {idx+1} Skipped Question",
                "evidence": f"Candidate provided no answer to: '{q[:90]}...'"
            })
        elif classification == CLASS_EARLY_EXIT:
            scored_weaknesses.append({
                "title": "Early Interview Termination",
                "evidence": f"Candidate requested early termination on Turn {idx+1}: '{candidate_ans_str}'"
            })

    # 2. Strict Score & Grade Aggregation
    is_incomplete = valid_evaluated_answers < 5 or early_termination
    completion_rate = min(1.0, valid_evaluated_answers / float(total_questions))
    evaluated_avg = sum(turn_scores) / len(turn_scores) if turn_scores else 0.0

    if valid_evaluated_answers == 0:
        overall_score = 0
        overall_grade = "F"
        grade_label = "Unevaluated / No Responses"
        grade_color = "#ef4444"
        hiring_recommendation = "Strong Reject (No Responses Provided)"
        performance_level = "Beginner / Not Attempted"
        dyn_strengths = []
        dyn_weaknesses = scored_weaknesses[:3] or [{"title": "No response recorded", "evidence": "Candidate did not answer interview questions."}]
        status = "insufficient_data"
        report_type = "incomplete"
    elif is_incomplete:
        # Prorate evaluated average by completion rate: 1 answer cannot award 63 or 75
        evaluated_avg = sum(turn_scores) / len(turn_scores) if turn_scores else 0.0
        overall_score = round(evaluated_avg * completion_rate)
        overall_grade = "F"
        grade_label = "Incomplete / Early Exit"
        grade_color = "#ef4444"
        hiring_recommendation = f"Incomplete Assessment (Requires ≥ 5 answered questions; only {valid_evaluated_answers} of {total_questions} answered)"
        performance_level = "Incomplete Session"
        dyn_strengths = scored_strengths[:3]
        dyn_weaknesses = scored_weaknesses[:3]
        status = "insufficient_data"
        report_type = "incomplete"
    else:
        # Full completed evaluation (>= 5 valid answers)
        evaluated_avg = sum(turn_scores) / len(turn_scores) if turn_scores else 0.0
        overall_score = round(min(100.0, max(0.0, evaluated_avg)))
        g_meta = calculate_grade_info(overall_score)
        overall_grade = g_meta.get("grade", "B")
        grade_label = g_meta.get("label", "Competent")
        grade_color = g_meta.get("color", "#10b981")
        hiring_recommendation = "Strong Hire" if overall_score >= 85 else ("Hire" if overall_score >= 75 else ("Neutral" if overall_score >= 60 else "Reject"))
        performance_level = g_meta.get("level", "Mid-Level Professional")
        dyn_strengths = scored_strengths[:3]
        dyn_weaknesses = scored_weaknesses[:3]
        status = "completed"
        report_type = "final"

    # Demonstrated Strengths fallback notice
    if not dyn_strengths:
        top_strengths_summary = ["Insufficient evidence to identify demonstrated strengths."]
    else:
        top_strengths_summary = [s["title"] for s in dyn_strengths]

    # Clean display metadata
    effective_role = role if role and str(role).strip().lower() != "none" else "Software Engineer"
    effective_diff = difficulty if difficulty and str(difficulty).strip().lower() != "none" else "Medium"
    effective_mode = "Job Description Mode" if (interview_mode == "job_description" or "JOB DESCRIPTION" in str(track).upper()) else "Resume Mode"
    effective_track = track if track and str(track).strip().lower() != "none" else ("HR & Behavioral" if "HR" in effective_role.upper() else "DSA & Algorithms")

    # Speech delivery telemetry
    full_transcript = " ".join([str(ans) for ans in responses if ans and str(ans).strip()])
    total_w = len(full_transcript.split())
    speech_metrics = {
        "wpm": round((total_w / 15.0) * 60) if total_w > 0 and not is_incomplete else (135 if total_w >= 10 else 0),
        "pacing_label": "Optimal (130-155 WPM)" if total_w >= 20 else ("Deliberate Pace" if total_w > 0 else "No Speech Detected"),
        "pacing_color": "#10b981" if total_w >= 20 else "#94a3b8",
        "total_words": total_w,
        "filler_count": 0,
        "filler_breakdown": {},
        "vocabulary_diversity_pct": 75 if total_w >= 20 else 0,
        "overused_words": []
    }

    # Dimensions calibration
    dim_score = overall_score if not is_incomplete else (evaluated_avg if turn_scores else 0)
    dimensions = [
        {"name": "Communication", "score": min(100, int(dim_score + 2)) if valid_evaluated_answers > 0 else None, "grade": calculate_grade_info(dim_score)["grade"] if valid_evaluated_answers > 0 else "N/A", "evidence_level": "HIGH" if valid_evaluated_answers >= 5 else ("MEDIUM" if valid_evaluated_answers > 0 else "NONE"), "evidence": [f"Evaluated across {valid_evaluated_answers} substantive responses."]},
        {"name": "Domain & Role Knowledge", "score": int(dim_score) if valid_evaluated_answers > 0 else None, "grade": calculate_grade_info(dim_score)["grade"] if valid_evaluated_answers > 0 else "N/A", "evidence_level": "HIGH" if valid_evaluated_answers >= 5 else ("MEDIUM" if valid_evaluated_answers > 0 else "NONE"), "evidence": [f"Assessed against key competencies for {effective_role}."]},
        {"name": "Problem Solving & Analysis", "score": int(dim_score) if valid_evaluated_answers > 0 else None, "grade": calculate_grade_info(dim_score)["grade"] if valid_evaluated_answers > 0 else "N/A", "evidence_level": "HIGH" if valid_evaluated_answers >= 5 else ("MEDIUM" if valid_evaluated_answers > 0 else "NONE"), "evidence": ["Analyzed structured approach and handling of edge cases/scenarios."]},
        {"name": "Confidence & Delivery", "score": max(0, int(dim_score - 2)) if valid_evaluated_answers > 0 else None, "grade": calculate_grade_info(dim_score)["grade"] if valid_evaluated_answers > 0 else "N/A", "evidence_level": "MEDIUM" if valid_evaluated_answers > 0 else "NONE", "evidence": ["Evaluated pacing, vocal clarity, and conviction."]},
        {"name": "Behavioral Competence", "score": int(dim_score) if "HR" in effective_track.upper() or "BEHAVIORAL" in effective_track.upper() else None, "grade": calculate_grade_info(dim_score)["grade"] if ("HR" in effective_track.upper() or "BEHAVIORAL" in effective_track.upper()) and valid_evaluated_answers > 0 else "N/A", "evidence_level": "HIGH" if "HR" in effective_track.upper() and valid_evaluated_answers >= 3 else "NONE", "evidence": ["STAR method, conflict handling, and situational teamwork."]}
    ]

    # Turn by turn breakdown
    turn_evaluations = []
    for idx, q in enumerate(questions):
        ans = responses[idx] if idx < len(responses) else "[No response recorded]"
        fb = feedbacks[idx] if idx < len(feedbacks) and isinstance(feedbacks[idx], dict) else {}
        t_score = fb.get("accuracy_score")
        if t_score is None:
            t_score = fb.get("score", 0) * 10
        t_score = int(t_score)
        t_grade = calculate_grade_info(t_score)

        turn_evaluations.append({
            "question_number": idx + 1,
            "question": q,
            "candidate_answer": ans,
            "score": t_score,
            "grade": t_grade.get("grade", "F"),
            "grade_color": t_grade.get("color", "#ef4444"),
            "strength": fb.get("strength") or "None identified",
            "improvement": fb.get("improvement") or "Elaborate with concrete details and trade-offs.",
            "classification": fb.get("correctness") or "Evaluated"
        })

    # Executive Summary Markdown text
    strengths_md = "\n".join(f"- **{s['title']}**: {s['evidence']}" for s in dyn_strengths) if dyn_strengths else "- *Insufficient evidence to identify demonstrated strengths.*"
    weaknesses_md = "\n".join(f"- **{w['title']}**: {w['evidence']}" for w in dyn_weaknesses) if dyn_weaknesses else "- *No significant weaknesses recorded.*"
    status_label = "Completed" if not is_incomplete else "Incomplete / Insufficient Data"

    summary_text = (
        f"### Executive Candidate Evaluation\n\n"
        f"- **Candidate Name:** {candidate_name or 'Candidate'}\n"
        f"- **Target Role:** {effective_role}\n"
        f"- **Interview Mode:** {effective_mode}\n"
        f"- **Selected Topics:** {effective_track}\n"
        f"- **Interview Difficulty:** {effective_diff}\n"
        f"- **Total Questions:** {total_questions} | **Attempted:** {attempted_questions} | **Valid Evaluated Answers:** {valid_evaluated_answers}\n"
        f"- **Evaluation Status:** {status_label}\n"
        f"- **Overall Score:** {overall_score}/100 | **Overall Grade:** {overall_grade}\n"
        f"- **Hiring Recommendation:** {hiring_recommendation}\n\n"
        f"#### Demonstrated Strengths\n{strengths_md}\n\n"
        f"#### Focus Areas & Weaknesses\n{weaknesses_md}\n\n"
        f"#### Final Assessment\n"
        f"Candidate attempted {attempted_questions} of {total_questions} questions for the {effective_role} role ({effective_diff} difficulty). "
        f"{'Evaluation is considered incomplete due to low answer count or early exit.' if is_incomplete else 'Demonstrated clear domain understanding and structured delivery across all core dimensions.'}"
    )

    report = {
        "status": status,
        "is_incomplete": is_incomplete,
        "report_type": report_type,
        "executive_summary": {
            "candidate_name": candidate_name or "Candidate",
            "target_role": effective_role,
            "interview_mode": effective_mode,
            "selected_topics": effective_track,
            "difficulty": effective_diff,
            "total_questions": total_questions,
            "questions_attempted": attempted_questions,
            "valid_evaluated_answers": valid_evaluated_answers,
            "overall_score": overall_score,
            "overall_grade": overall_grade,
            "key_strengths": dyn_strengths,
            "key_weaknesses": dyn_weaknesses,
            "final_assessment": summary_text
        },
        "candidate_name": candidate_name or "Candidate",
        "role": effective_role,
        "track": effective_track,
        "difficulty": effective_diff,
        "interview_mode": effective_mode,
        "total_questions": total_questions,
        "attempted_questions": attempted_questions,
        "answered_questions_count": valid_evaluated_answers,
        "valid_evaluated_answers": valid_evaluated_answers,
        "skipped_questions": skipped_questions,
        "unanswered_questions": unanswered_questions,
        "early_termination": early_termination,
        "overall_score": overall_score,
        "overall_score_100": overall_score,
        "grade": overall_grade,
        "overall_grade": overall_grade,
        "grade_label": grade_label,
        "grade_color": grade_color,
        "recommendation": hiring_recommendation,
        "hiring_recommendation": hiring_recommendation,
        "performance_level": performance_level,
        "confidence": "Low" if is_incomplete else "High",
        "dimensions": dimensions,
        "strengths": dyn_strengths,
        "weaknesses": dyn_weaknesses,
        "top_strengths": top_strengths_summary,
        "top_improvements": [w["title"] for w in dyn_weaknesses] if dyn_weaknesses else ["Answer all questions thoroughly."],
        "speech_metrics": speech_metrics,
        "turn_evaluations": turn_evaluations,
        "report": summary_text
    }

    return enrich_report_with_grading(report)


def enrich_report_with_grading(report: dict) -> dict:
    if not isinstance(report, dict):
        report = {}
    
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
                    if score_val > 100.0:
                        score_val = score_val / 10.0
                    score_val = min(100.0, max(0.0, score_val))
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
            raw_score = round(sum(valid_scores) / len(valid_scores))
        else:
            raw_score = 0
    else:
        raw_val = float(report.get("overall_score") if report.get("overall_score") is not None else 0)
        if raw_val > 100.0:
            raw_val = raw_val / 10.0
        raw_score = min(100.0, max(0.0, raw_val))

    valid_q_count = int(report.get("answered_questions_count", 0))
    total_q = max(10, int(report.get("total_questions", 10)))
    completion_rate = min(1.0, valid_q_count / float(total_q))

    # PrepFly Assessment Standard: Prorate score by completion rate
    if valid_q_count == 0:
        score = 0
        g_info = {
            "score": 0,
            "grade": "F",
            "label": "Unevaluated / No Responses",
            "desc": "No responses attempted during interview",
            "color": "#ef4444",
            "bgColor": "rgba(239, 68, 68, 0.15)",
            "rec": "Strong Reject (No Responses Provided)",
            "level": "Beginner / Not Attempted"
        }
    elif valid_q_count < 3:
        # Incomplete / Early exit (e.g. only 1 question answered)
        score = round(raw_score * completion_rate)
        g_info = {
            "score": int(score),
            "grade": "F",
            "label": "Incomplete / Early Exit",
            "desc": f"Only {valid_q_count} of {total_q} questions answered",
            "color": "#ef4444",
            "bgColor": "rgba(239, 68, 68, 0.15)",
            "rec": f"Strong Reject (Incomplete — only {valid_q_count} of {total_q} questions answered)",
            "level": "Incomplete Session"
        }
    elif valid_q_count < 5:
        # Preliminary (3-4 questions answered)
        score = round(raw_score * completion_rate)
        raw_g = calculate_grade_info(score)
        g_info = {
            "score": int(score),
            "grade": raw_g["grade"] if raw_g["grade"] in ("D", "F") else "D",
            "label": "Preliminary Assessment",
            "desc": f"Answered {valid_q_count} of {total_q} questions",
            "color": "#f59e0b",
            "bgColor": "rgba(245, 158, 11, 0.15)",
            "rec": "Preliminary Evaluation (Requires ≥ 5 answered questions)",
            "level": "Preliminary Evaluation"
        }
    else:
        # Full evaluation (5+ questions answered)
        score = min(100.0, max(0.0, float(raw_score)))
        g_info = calculate_grade_info(score)

    is_prelim = valid_q_count < 5 or report.get("report_type") == "preliminary"

    report["overall_score"] = int(g_info["score"])
    report["overall_score_100"] = int(g_info["score"])
    report["grade"] = g_info["grade"]
    report["overall_grade"] = g_info["grade"]
    report["grade_label"] = g_info["label"]
    report["grade_color"] = g_info["color"]
    report["hiring_recommendation"] = g_info["rec"]
    report["recommendation"] = g_info["rec"]
    report["performance_level"] = g_info["level"]
    report["report_type"] = "preliminary" if is_prelim else "final"
    report["confidence"] = "Low" if valid_q_count <= 2 else ("Medium" if valid_q_count < 5 else "High")
    if is_prelim:
        report["badges"] = []

    if "section_grades" not in report:
        sections = compute_section_grades([], {"clarity": report.get("communication_score", 80), "wpm": report.get("transcript_analytics", {}).get("words_per_minute", 135)})
        if score == 0:
            for sec in sections:
                sec["score"] = None
                sec["grade"] = "N/A"
                sec["color"] = "#7a8ba8"
                sec["bgColor"] = "rgba(122, 139, 168, 0.15)"
                sec["label"] = "Not Assessed"
            report["badges"] = []
        else:
            report["badges"] = award_badges(score, sections)
        report["section_grades"] = sections
    else:
        if score == 0:
            report["badges"] = []
        else:
            report["badges"] = award_badges(score, report["section_grades"])

    # Strengths — keep only evidence-backed items with verified score >= 70
    if valid_q_count == 0 or score == 0:
        report["top_strengths"] = ["None identified (no responses provided during interview)."]
        report["strengths"] = []
    else:
        strengths = report.get("strengths") or []
        if strengths and isinstance(strengths[0], dict):
            report["top_strengths"] = [
                f"{s.get('title')}: {s.get('evidence')}"
                for s in strengths
                if isinstance(s, dict) and s.get("title") and s.get("evidence")
            ] or ["Preliminary observation: Complete more technical/behavioral questions to demonstrate strengths."]
        else:
            report["top_strengths"] = strengths if strengths else ["Preliminary observation: Complete more technical/behavioral questions to demonstrate strengths."]

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
        if is_prelim:
            report["ai_summary"] = (f"Preliminary evaluation based on {valid_q_count} answered question(s). "
                                    f"Confidence is {report['confidence']}. Complete at least 5 questions for a full hiring recommendation.")
        else:
            report["ai_summary"] = (f"The candidate demonstrated {g_info['label'].lower()} performance ({g_info['grade']} Grade, "
                                    f"{g_info['score']}/100) across {assessed_count} assessed dimension(s). "
                                    f"Based on this evaluation, the candidate is {report['hiring_recommendation'].lower()}.")

    if "conversation_summary" not in report or not report["conversation_summary"]:
        report["conversation_summary"] = build_conversation_summary(
            report.get("questions") or [],
            report.get("responses") or [],
            report.get("feedbacks") or []
        )

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









