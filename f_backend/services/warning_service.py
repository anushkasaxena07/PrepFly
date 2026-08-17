import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from services.embedding_service import generate_embedding, cosine_similarity
from services.gemini import get_flash_model, get_pro_model
from langchain_core.messages import HumanMessage

logger = logging.getLogger("interviewsystem.warnings")

EVASIVE_PHRASES = [
    "i don't know", "dont know", "no idea", "pass", "skip", "next question",
    "can't answer", "cannot answer", "dunno", "whatever", "idk", "no comment"
]

def get_supabase():
    import app
    return app.supabase

def detect_warning(question: str, answer: str, evaluation: dict) -> tuple[bool, str]:
    """
    Evaluates whether a candidate's answer represents a warning-worthy response
    (e.g., evasive answer, total refusal, off-topic rambling, or zero score).
    """
    answer_clean = (answer or "").strip().lower()
    score = float(evaluation.get("score", 7.0)) if isinstance(evaluation, dict) else 7.0
    
    # 1. Evasive Phrase Detection
    for phrase in EVASIVE_PHRASES:
        if phrase in answer_clean or answer_clean == phrase:
            return True, f"Candidate gave an evasive answer ('{answer_clean[:40]}...')"
            
    # 2. Ultra-short non-answer (< 3 words for technical questions)
    words = [w for w in answer_clean.split() if w]
    if len(words) < 3 and score < 4.0:
        return True, f"Candidate gave an incomplete or non-informative response ({len(words)} words)"

    # 3. Severe score penalty (< 2.5/10)
    if score < 2.5:
        return True, f"Candidate response failed core technical requirements (score: {score}/10)"

    return False, ""

def record_warning(session_id: str, question: str, answer: str, reason: str, warning_count: int) -> Dict[str, Any]:
    """
    Generates 768-dim vector embedding for warning event and stores record in Supabase database.
    """
    warning_text = f"Question: {question}\nAnswer: {answer}\nWarning Reason: {reason}"
    vector_emb = generate_embedding(warning_text)
    
    warning_record = {
        "session_id": session_id,
        "warning_number": warning_count,
        "question": question,
        "answer": answer,
        "reason": reason,
        "embedding": vector_emb,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        supabase = get_supabase()
        supabase.table("interview_warnings").insert({
            "session_id": session_id,
            "warning_number": warning_count,
            "question": question,
            "answer": answer,
            "reason": reason,
            "created_at": warning_record["timestamp"]
        }).execute()
        logger.info(f"Recorded Warning #{warning_count} for session '{session_id}' with vector embedding.")
    except Exception as err:
        logger.warning(f"Warning DB record notice (using session fallback): {err}")
        
    return warning_record

def recall_and_evaluate_warnings(session_id: str, warning_records: List[Dict[str, Any]], current_warning: Dict[str, Any]) -> Dict[str, Any]:
    """
    Triggered when warning_count >= 3:
    1. Computes Cosine Similarity across past warning vector embeddings.
    2. Ranks past warnings to extract semantic behavioral patterns.
    3. Prompts Gemini AI to make deterministic escalation decision (terminate | strict_warning | continue).
    """
    if not warning_records:
        warning_records = [current_warning]

    current_vec = current_warning.get("embedding") or generate_embedding(current_warning.get("reason", ""))

    # Rank past warnings by vector similarity against current warning
    ranked_warnings = []
    for w in warning_records:
        w_vec = w.get("embedding") or generate_embedding(w.get("reason", ""))
        sim = cosine_similarity(current_vec, w_vec)
        ranked_warnings.append({
            "warning_number": w.get("warning_number", 1),
            "question": w.get("question", ""),
            "answer": w.get("answer", ""),
            "reason": w.get("reason", ""),
            "similarity_score": round(sim, 4)
        })

    ranked_warnings.sort(key=lambda x: x["similarity_score"], reverse=True)

    recalled_block_lines = []
    for rw in ranked_warnings:
        recalled_block_lines.append(
            f"- Warning #{rw['warning_number']} [Semantic Match: {rw['similarity_score']*100:.1f}%]:\n"
            f"  Question: {rw['question']}\n"
            f"  Candidate Answer: {rw['answer']}\n"
            f"  Reason: {rw['reason']}"
        )
    recalled_text_block = "\n".join(recalled_block_lines)

    eval_prompt = f"""You are Ava, Senior Technical Recruiter at PrepFly.
The candidate has accumulated 3 warnings during this live interview session.

SEMANTIC VECTOR RECALL OF CANDIDATE WARNING HISTORY:
{recalled_text_block}

DECISION MANDATE:
Analyze the candidate's persistent pattern of behavior across these 3 warnings.
Determine whether to:
1. "terminate": End the interview immediately due to repeated evasive non-answers, lack of engagement, or refusal to attempt core questions.
2. "strict_warning": Issue a stern final warning to the candidate before termination.
3. "continue": Allow candidate to proceed if answers show genuine effort despite technical difficulty.

Return ONLY valid JSON with no markdown wrapping:
{{
  "action": "terminate | strict_warning | continue",
  "reason": "<explanation of decision based on recalled warning patterns>",
  "message_to_candidate": "<what Ava actually says to candidate out loud — polite, professional, firm>"
}}"""

    model = get_pro_model(temperature=0.3)
    try:
        response = model.invoke([HumanMessage(content=eval_prompt)])
        raw_text = response.content.strip()
        
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            if lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].startswith("```"): lines = lines[:-1]
            raw_text = "\n".join(lines).strip()

        data = json.loads(raw_text)
        return {
            "action": data.get("action", "terminate"),
            "reason": data.get("reason", "Persistent evasive responses across 3 warnings."),
            "message_to_candidate": data.get("message_to_candidate", "We have reached 3 warnings due to repeated evasive answers. We will wrap up the interview session here today. Thank you for your time.")
        }
    except Exception as err:
        logger.error(f"Error evaluating 3-warning recall decision: {err}")
        return {
            "action": "terminate",
            "reason": "Accumulated 3 warning events for non-attempted questions.",
            "message_to_candidate": "We have reached 3 warnings for repeated evasive responses. We'll end the interview session here today."
        }
