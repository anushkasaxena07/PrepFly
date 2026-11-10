import os
import json
import random
import re
import time
import urllib.request
from langchain_core.messages import HumanMessage
from services.ai_config import AI_INTERVIEWER, AVA_SYSTEM_PROMPT, build_ava_system_prompt
from services.topic_engine import (
    validate_topic_question,
    validate_jd_question,
    is_hr_or_non_technical_role,
    get_curated_fallback_question,
    normalize_topic_identifier
)

GEMINI_MODEL_CANDIDATES = (
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
)
_UNAVAILABLE_GEMINI_MODELS = set()
_DISCOVERED_MODELS_CACHE = {"ts": 0.0, "models": []}


def is_test_gemini_key(api_key: str) -> bool:
    if not api_key or not isinstance(api_key, str):
        return True
    low = api_key.lower()
    return api_key.startswith("test-") or "dummy" in low or os.getenv("ENVIRONMENT") == "test" or os.getenv("FLASK_ENV") == "test"


def is_model_not_found_error(err: Exception) -> bool:
    s = str(err).lower()
    return any(tok in s for tok in ("404", "not_found", "is not found", "no longer available", "not supported for generatecontent"))


def is_transient_gemini_error(err: Exception) -> bool:
    s = str(err).lower()
    return any(tok in s for tok in ("503", "504", "429", "unavailable", "deadline", "timed out", "timeout", "resource exhausted"))


def mark_gemini_model_unavailable(model_name: str) -> None:
    if model_name:
        _UNAVAILABLE_GEMINI_MODELS.add(str(model_name).replace("models/", ""))


def discover_gemini_flash_models(api_key: str, timeout: float = 4.0) -> list:
    if is_test_gemini_key(api_key):
        return []
    now = time.monotonic()
    if _DISCOVERED_MODELS_CACHE["models"] and (now - _DISCOVERED_MODELS_CACHE["ts"]) < 300.0:
        return list(_DISCOVERED_MODELS_CACHE["models"])
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        flash_models = []
        for m in payload.get("models", []):
            name = str(m.get("name", "")).replace("models/", "")
            methods = m.get("supportedGenerationMethods") or []
            low = name.lower()
            if "generateContent" in methods and "flash" in low and not any(x in low for x in ("tts", "image", "audio", "live", "8b")):
                flash_models.append(name)
        # Prefer newer flash versions first
        def _rank(name: str):
            for idx, pref in enumerate(("gemini-3.8", "gemini-3.5", "gemini-3", "gemini-2.5", "gemini-2.0", "gemini-1.5")):
                if pref in name:
                    return (0, idx, len(name), name)
            return (1, 99, len(name), name)
        flash_models.sort(key=_rank)
        _DISCOVERED_MODELS_CACHE["ts"] = now
        _DISCOVERED_MODELS_CACHE["models"] = flash_models
        return list(flash_models)
    except Exception:
        return []


def get_fallback_gemini_models(api_key: str, exclude_model: str = "", include_discovery: bool = True) -> list:
    excluded = {str(exclude_model).replace("models/", "")} if exclude_model else set()
    excluded.update(_UNAVAILABLE_GEMINI_MODELS)
    candidates = list(GEMINI_MODEL_CANDIDATES)
    if include_discovery and not is_test_gemini_key(api_key):
        candidates.extend(discover_gemini_flash_models(api_key))
    seen = set()
    ordered = []
    for name in candidates:
        clean = str(name).replace("models/", "")
        if clean and clean not in excluded and clean not in seen:
            seen.add(clean)
            ordered.append(clean)
    return ordered


def safe_invoke_llm(chat_model, prompt_content):
    if not chat_model:
        return None

    api_key = getattr(chat_model, "google_api_key", None) or os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_INTERVIEW_KEY")
    if (isinstance(api_key, str) and (api_key.startswith("test-") or "dummy" in api_key.lower())) or os.getenv("ENVIRONMENT") == "test" or os.getenv("FLASK_ENV") == "test":
        return None

    def _extract_text(content):
        if not content:
            return None
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
            return "\n".join(parts).strip()
        return str(content).strip()

    primary_name = str(getattr(chat_model, "model", None) or getattr(chat_model, "model_name", None) or "")
    try:
        res = chat_model.invoke([HumanMessage(content=prompt_content)])
        if res and hasattr(res, "content"):
            txt = _extract_text(res.content)
            if txt:
                return txt
    except Exception as e_prim:
        if is_model_not_found_error(e_prim):
            mark_gemini_model_unavailable(primary_name)
        api_key = getattr(chat_model, "google_api_key", None) or os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_INTERVIEW_KEY")
        if is_test_gemini_key(api_key):
            return None
        print(f"[AI_SERVICE NOTICE] Primary model failed ({e_prim}), checking fallback models...")
        if api_key:
            for alt_name in get_fallback_gemini_models(api_key, exclude_model=primary_name, include_discovery=is_model_not_found_error(e_prim)):
                try:
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    alt_chat = ChatGoogleGenerativeAI(api_key=api_key, model=alt_name, temperature=0.6, max_retries=0, timeout=14)
                    res = alt_chat.invoke([HumanMessage(content=prompt_content)])
                    if res and hasattr(res, "content"):
                        txt = _extract_text(res.content)
                        if txt:
                            return txt
                except Exception as e_alt:
                    if is_model_not_found_error(e_alt):
                        mark_gemini_model_unavailable(alt_name)
                    continue
    return None

STAGES = [
    "Greeting & Icebreaker",
    "Icebreaker & Background",
    "Resume Anchor Transition",
    "Core Technical & Project Discussion",
    "System Trade-offs & Deep Dive",
    "Behavioral & Problem Solving",
    "Closing & Candidate Wrap-up"
]

PHASE_1_GREETINGS = [
    "Hey there! I'm Ava. Really glad to connect with you today! Before we get into technical stuff, how's your day going so far?",
    "Hi! I'm Ava, senior recruiter here. Think of this as a relaxed conversation rather than a exam. How are you feeling today?",
    "Hey! I'm Ava. Excited to chat with you today! How's your week been treating you so far?"
]

PHASE_2_ICEBREAKERS = [
    "Got it, that makes total sense! Have you been doing many of these interviews lately, or is this your first one today?",
    "Right, I hear you! How are things on your side today — taking a quick break from coding or projects?",
    "Hmm, interesting! Always good to take a breather. What's something fun or interesting you've worked on recently outside of work?"
]

PHASE_3_TRANSITIONS = [
    "Right, that's relatable! Looking at your background, I noticed your work with software engineering and system architecture — what originally drew you into building software?",
    "Okay so, looking over your background, something that caught my eye was your hands-on project experience. What's the project you're most proud of?",
    "Got it! I see you have experience across frontend and backend systems. What pushed you to dive deeper into full-stack development?"
]

PHASE_4_FALLBACKS = [
    "What was the hardest technical trade-off or architectural challenge you faced in your recent project, and how did you resolve it?",
    "When building backend services or database queries, how do you usually ensure high availability and fast response times?",
    "Could you share a situation where a production deployment or bug didn't go as planned, and how you and your team handled it?",
    "In your previous projects, how did you decide between using SQL vs NoSQL databases for data persistence?",
    "Tell me about a time when you had to learn a brand new framework or tool under a very tight deadline — how did you approach it?",
    "When explaining complex system architecture to non-technical stakeholders or teammates, how do you structure your explanation?",
    "Looking back at your recent projects, is there a technical design choice you made that you would approach differently now?"
]

def get_current_stage(question_index, total_questions=5):
    if total_questions == 5:
        if question_index == 1:
            return "Phase 1: Greeting & Icebreaker"
        elif question_index == 2:
            return "Phase 2: Icebreaker & Background"
        elif question_index == 3:
            return "Phase 3: Transition into Resume"
        elif question_index == 4:
            return "Phase 4: Core Technical Discussion"
        elif question_index == 5:
            return "Phase 5: System Trade-offs & Deep Dive"
        else:
            return "Phase 7: Natural Wrap-up"
    else:
        if question_index == 1:
            return "Phase 1: Greeting & Icebreaker"
        elif question_index == 2:
            return "Phase 2: Background & Experience"
        elif question_index == 3:
            return "Phase 3: Resume Deep-Dive"
        elif question_index == 4:
            return "Phase 4: Architecture & Design Decisions"
        elif question_index == 5:
            return "Phase 5: Core Technical Concepts"
        elif question_index == 6:
            return "Phase 6: Performance & Optimization"
        elif question_index == 7:
            return "Phase 7: Reliability & Edge Cases"
        elif question_index == 8:
            return "Phase 8: Scale & Trade-offs"
        elif question_index == 9:
            return "Phase 9: Behavioral & Leadership (STAR)"
        elif question_index >= 10:
            return "Phase 10: Retrospective & Closing"
        else:
            return "Phase 10: Retrospective & Closing"

def is_semantically_repetitive(new_q: str, existing_questions: list) -> bool:
    """Detects exact duplicates and high semantic/keyword overlaps across questions."""
    if not new_q or not existing_questions:
        return False
    
    filler = {"tell", "about", "could", "would", "please", "describe", "explain", "what", "which", "your", "with", "have", "from", "that", "this", "some", "like", "how", "why"}
    
    def stem(w):
        return re.sub(r'(ing|ed|es|s)$', '', w)
        
    clean_new = set(stem(w) for w in re.findall(r'\b[a-z]{3,}\b', new_q.lower())) - filler
    if not clean_new:
        return False

    for old_q in existing_questions:
        if not old_q:
            continue
        if new_q.strip().lower() == old_q.strip().lower():
            return True
            
        clean_old = set(stem(w) for w in re.findall(r'\b[a-z]{3,}\b', old_q.lower())) - filler
        if not clean_old:
            continue
        
        common = clean_new.intersection(clean_old)
        union = clean_new.union(clean_old)
        
        # If 2 or more key domain words match (e.g. ['project', 'resume'] or ['process', 'thread'])
        if len(common) >= 2 and (len(common) / len(clean_new) >= 0.35 or len(common) / len(clean_old) >= 0.35):
            return True
            
        similarity = len(common) / len(union) if union else 0
        if similarity >= 0.35:
            return True
    return False


def generate_dynamic_question(
    resume_text,
    previous_questions=None,
    question_index=1,
    last_score=None,
    last_answer=None,
    category=None,
    difficulty=None,
    responses=None,
    chat_model=None,
    candidate_name="Candidate",
    role=None,
    job_description=None,
    allowed_topics=None
):
    previous_questions = previous_questions or []
    responses = responses or []
    stage_name = get_current_stage(question_index)
    ai_name = AI_INTERVIEWER["name"]

    # Identify Mode & Role Context
    is_no_resume = bool(
        (resume_text and ("No Resume Provided" in resume_text or "JOB DESCRIPTION" in resume_text or "JOB PROFILE" in resume_text))
        or (job_description and not resume_text)
    )
    effective_role = role or (category if category and "Software" in category else "Software Engineer")
    effective_jd = job_description or (resume_text if is_no_resume else "")
    is_hr = is_hr_or_non_technical_role(effective_role, effective_jd) or (
        category and "HR" in category.upper() and "DSA" not in category.upper()
    )

    # 1. Turn 1 GUARANTEE: Warm greeting and casual, low-stakes icebreaker (No technical jargon on Turn 1)
    if question_index == 1:
        first_name = candidate_name.strip().split()[0] if candidate_name and candidate_name.strip() and candidate_name.lower() != "candidate" else ""
        name_str = f" {first_name}" if first_name else ""
        if is_hr:
            greeting = f"Hi{name_str}! I'm Ava, your AI interviewer today. It's really wonderful to meet you! Before we dive into questions for the {effective_role} role, how are you feeling today and how is your day going so far?"
        else:
            greeting = f"Hi{name_str}! I'm Ava, your AI interviewer today. It's really wonderful to meet you! Before we dive into questions for the {effective_role} role, how are you feeling today and how is your day going so far?"
        return greeting, "Phase 1: Greeting & Icebreaker", False

    # 2. Handle Voice / Text Commands (Repeat)
    if last_answer and last_answer.strip().lower() in ["repeat", "can you repeat the question", "pardon"]:
        if previous_questions:
            return previous_questions[-1], "Repeat", False

    # Build conversation history Q&A string
    history_lines = []
    for idx, q in enumerate(previous_questions):
        ans = responses[idx] if idx < len(responses) else (last_answer if idx == len(previous_questions)-1 else "")
        history_lines.append(f"Turn {idx+1} Q: {q}\nTurn {idx+1} Candidate A: {ans if ans else '[Pending]'}")
    conv_history_str = "\n\n".join(history_lines) if history_lines else "None (Initial Turn)"

    # Build explicit track & phase guidance based on selected topics / JD
    cat_clean = (category or "").upper()
    if is_no_resume:
        if is_hr:
            track_instruction = f"""TRACK: HUMAN RESOURCES (HR) & TALENT MANAGEMENT INTERVIEW
STRICT MANDATE: Every question from Turn 2 onwards MUST be strictly and directly based on the provided HR Job Description and Target Role: {effective_role}
{effective_jd[:2500]}
DO NOT ask software engineering, programming, coding, algorithmic, or technical architecture questions under any circumstance.
Focus exclusively on HR responsibilities: talent acquisition, employee relations, onboarding, compliance (POSH/statutory), performance management, and HR operations."""
            phase_guidance = f"PHASE: HR JOB DESCRIPTION ROUND (Turn {question_index}). Previous Candidate Answer: '{last_answer}'. Briefly acknowledge, then ask an authentic HR scenario or workflow question strictly grounded in the Job Description."
        else:
            track_instruction = f"""TRACK: JOB DESCRIPTION SPECIFIC INTERVIEW FOR ROLE: {effective_role}
STRICT MANDATE: Every question from Turn 2 onwards MUST be strictly and directly based on the provided Job Description and Target Role:
{effective_jd[:2500]}
DO NOT ask questions on unrelated tools, technologies, or imaginary projects not mentioned in the Job Description.
DO NOT invent candidate experience or pretend to have read an uploaded resume."""
            phase_guidance = f"PHASE: TARGET JOB DESCRIPTION ROUND (Turn {question_index}). Previous Candidate Answer: '{last_answer}'. React briefly (1 sentence), then ask a targeted question STRICTLY assessing the skills, tools, and responsibilities demanded in the Job Description."
    elif "DSA" in cat_clean or "ALGORITHM" in cat_clean:
        track_instruction = """TRACK: DATA STRUCTURES & ALGORITHMS (DSA)
STRICT MANDATE: Ask EXCLUSIVELY on data structures (Arrays, Hash Maps, Trees, Graphs, Heaps, Dynamic Programming), algorithmic problem solving, edge cases, and Big-O time/space complexity.
DO NOT ask high-level system design, computer networks, database ACID, or behavioral questions."""
        if question_index == 2:
            phase_guidance = f"PHASE: DSA CODING PROBLEM 1. Previous Candidate Answer: '{last_answer}'. Present a concrete DSA problem (Arrays, Strings, Hash Maps, or Two Pointers). Ask for approach and time/space complexity."
        elif question_index == 3:
            phase_guidance = f"PHASE: DSA FOLLOW-UP & OPTIMIZATION. Previous Candidate Answer: '{last_answer}'. Probe edge cases, memory constraints, or optimizing algorithmic complexity."
        elif question_index == 4:
            phase_guidance = f"PHASE: DSA CODING PROBLEM 2. Previous Candidate Answer: '{last_answer}'. Present a problem on Trees, Graphs, or Dynamic Programming/Recursion."
        else:
            phase_guidance = f"PHASE: DSA TRADEOFFS & COMPLEXITY (Turn {question_index}). Previous Candidate Answer: '{last_answer}'. Probe worst-case time/space complexity and algorithmic trade-offs."
    elif "SYSTEM" in cat_clean or "DESIGN" in cat_clean:
        track_instruction = """TRACK: SYSTEM DESIGN & ARCHITECTURE
STRICT MANDATE: Ask EXCLUSIVELY on distributed systems, microservices, load balancers, database sharding/indexing, caching (Redis), message queues (Kafka), and high availability.
DO NOT ask coding syntax, leetcode problems, or behavioral STAR questions."""
        phase_guidance = f"PHASE: SYSTEM DESIGN ARCHITECTURE (Turn {question_index}). Previous Candidate Answer: '{last_answer}'. Probe high-scale architectural design, data modeling, caching, and resilience."
    elif "FUNDAMENTAL" in cat_clean or "CS" in cat_clean or "CORE" in cat_clean:
        track_instruction = """TRACK: COMPUTER SCIENCE FUNDAMENTALS
STRICT MANDATE: Ask EXCLUSIVELY on core CS pillars: Operating Systems (processes vs threads, virtual memory), Computer Networks (TCP/UDP, DNS, HTTP/S), DBMS (ACID, indexing, transactions), and OOP/SOLID design.
DO NOT ask large-scale distributed system design or generic HR questions."""
        phase_guidance = f"PHASE: CS FUNDAMENTALS CORE (Turn {question_index}). Previous Candidate Answer: '{last_answer}'. Ask a concrete CS fundamentals question."
    elif "HR" in cat_clean or "BEHAVIORAL" in cat_clean or is_hr:
        track_instruction = """TRACK: HR & BEHAVIORAL INTERVIEW
STRICT MANDATE: Ask EXCLUSIVELY behavioral, leadership, teamwork, conflict resolution, situational judgment, and STAR-method questions (Situation, Task, Action, Result).
DO NOT ask technical coding, syntax, or systems architecture questions."""
        phase_guidance = f"PHASE: BEHAVIORAL STAR SCENARIO (Turn {question_index}). Previous Candidate Answer: '{last_answer}'. Ask a targeted behavioral question using the STAR method."
    else:
        track_instruction = f"""TRACK: RESUME BASED INTERVIEW FOR {effective_role}
STRICT MANDATE: Ask questions directly tied to candidate's past projects, achievements, and tech stack from their resume without drifting into unselected topics."""
        phase_guidance = f"PHASE: RESUME PROJECT ROUND (Turn {question_index}). Previous Candidate Answer: '{last_answer}'. Dive into a specific project from their resume."

    resume_has_text = bool(resume_text and not is_no_resume)
    system_prompt = build_ava_system_prompt(
        role=effective_role,
        track=category or ("HR & Behavioral" if is_hr else "Resume Based"),
        difficulty=difficulty or "Medium",
        experience_level="1-3 Years",
        duration_minutes=20,
        resume_provided=resume_has_text,
        resume_data=resume_text[:2000] if resume_has_text else "None",
        candidate_name=candidate_name
    )

    prev_q_list = "\n".join(f"- {q}" for q in previous_questions) if previous_questions else "None (first turn)"

    prompt = f"""{system_prompt}

DYNAMIC CONTEXT DATA FOR THIS TURN:
- conversation_history:
{conv_history_str}

PREVIOUSLY ASKED QUESTIONS (DO NOT REPEAT):
{prev_q_list}

LATEST CANDIDATE RESPONSE:
"{last_answer or 'None'}"

{track_instruction}
{phase_guidance}

CRITICAL ANTI-REPETITION & TOPIC INTEGRITY MANDATE:
- You MUST NOT repeat, rephrase, or ask about the same topic or scenario as any question in PREVIOUSLY ASKED QUESTIONS.
- The question MUST strictly conform to the allowed topic constraints.

Return ONLY valid JSON with no markdown codeblock wrapping:
{{
  "acknowledgment": "<1 short sentence reacting to their previous answer, or empty string if first question>",
  "message": "<what Ava actually says out loud this turn - acknowledgment + question combined into natural speech>",
  "question_type": "resume | project | technical | behavioral | followup | closing",
  "stage": "greeting | resume_discussion | project_deepdive | technical | behavioral | closing",
  "difficulty_delta": "increase | decrease | same",
  "targets_resume_item": "<specific skill/project referenced, or null>",
  "is_followup": true
}}
"""

    needs_followup = False
    try:
        raw_output = safe_invoke_llm(chat_model, prompt)
        if not raw_output:
            raise ValueError("No response from LLM candidates")

        raw_output = raw_output.strip()
        if raw_output.startswith("```"):
            lines_out = raw_output.split("\n")
            if lines_out[0].startswith("```"):
                lines_out = lines_out[1:]
            if lines_out and lines_out[-1].startswith("```"):
                lines_out = lines_out[:-1]
            raw_output = "\n".join(lines_out).strip()

        q_text = ""
        try:
            parsed = json.loads(raw_output)
            if isinstance(parsed, dict):
                q_text = parsed.get("message") or parsed.get("question") or ""
                needs_followup = bool(parsed.get("is_followup", False))
            elif isinstance(parsed, str):
                q_text = parsed
        except Exception:
            msg_match = re.search(r'"message"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', raw_output)
            if msg_match:
                q_text = msg_match.group(1).replace('\\"', '"').replace('\\n', ' ').strip()
            else:
                q_text = raw_output

        if q_text.startswith('{') and '"message"' in q_text:
            msg_match = re.search(r'"message"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', q_text)
            if msg_match:
                q_text = msg_match.group(1).replace('\\"', '"').replace('\\n', ' ').strip()

        if (q_text.startswith('"') and q_text.endswith('"')) or (q_text.startswith("'") and q_text.endswith("'")):
            q_text = q_text[1:-1].strip()

        # Check for semantic repetition
        if is_semantically_repetitive(q_text, previous_questions):
            raise ValueError(f"Duplicate or overly similar question generated by LLM: {q_text}")

        # ── MANDATORY TOPIC & JD VALIDATION GATE ──────────────────────────
        if is_no_resume:
            is_valid, reason = validate_jd_question(q_text, effective_role, effective_jd)
            if not is_valid:
                print(f"[REJECTED NON-JD QUESTION] {reason}. Regenerating from curated bank.")
                q_text = get_curated_fallback_question(
                    category=category or ("HR_JOB_DESCRIPTION" if is_hr else "GENERAL"),
                    role=effective_role,
                    job_description=effective_jd,
                    question_index=question_index,
                    previous_questions=previous_questions
                )
        else:
            topics_to_check = allowed_topics or [category or "GENERAL"]
            is_valid, detected_topic, reason = validate_topic_question(q_text, topics_to_check)
            if not is_valid:
                print(f"[REJECTED OFF-TOPIC QUESTION] {reason}. Regenerating from curated bank.")
                q_text = get_curated_fallback_question(
                    category=category or "DSA",
                    role=effective_role,
                    job_description=effective_jd,
                    question_index=question_index,
                    previous_questions=previous_questions
                )

        return q_text, stage_name, needs_followup

    except Exception as e:
        print(f"Dynamic question generation fallback notice ({e}), selecting strictly validated topic question:")
        fallback_choice = get_curated_fallback_question(
            category=category or ("HR_JOB_DESCRIPTION" if is_hr else "DSA"),
            role=effective_role,
            job_description=effective_jd,
            question_index=question_index,
            previous_questions=previous_questions
        )
        return fallback_choice, stage_name, False


def generate_hint(question, resume_text, chat_model):
    ai_name = AI_INTERVIEWER["name"]
    prompt = f"""You are {ai_name}, a supportive and professional AI interviewer. The candidate asked for a hint on this question:
Question: {question}
Candidate Profile/Resume: {resume_text[:1000]}

Provide a small, helpful, 1-2 sentence hint that guides their thought process without giving away the complete answer directly."""
    try:
        from services.cache_service import get_cached_ai_response, save_cached_ai_response
        cached_hint = get_cached_ai_response(prompt)
        if cached_hint:
            return cached_hint
    except Exception:
        pass

    try:
        hint_text = safe_invoke_llm(chat_model, prompt)
        if not hint_text:
            raise ValueError("No response from LLM for hint")
        try:
            from services.cache_service import save_cached_ai_response
            save_cached_ai_response(prompt, hint_text, ttl=86400)
        except Exception:
            pass
        return hint_text
    except Exception as e:
        print(f"Generate hint error: {e}")
        return "Focus on breaking the problem down into core components and using the STAR framework (Situation, Task, Action, Result)."
