import os
import json
import random
import re
from langchain_core.messages import HumanMessage
from services.ai_config import AI_INTERVIEWER, AVA_SYSTEM_PROMPT, build_ava_system_prompt

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

    try:
        res = chat_model.invoke([HumanMessage(content=prompt_content)])
        if res and hasattr(res, "content"):
            txt = _extract_text(res.content)
            if txt:
                return txt
    except Exception as e_prim:
        api_key = getattr(chat_model, "google_api_key", None) or os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_INTERVIEW_KEY")
        if not api_key or (isinstance(api_key, str) and (api_key.startswith("test-") or "dummy" in api_key.lower())) or os.getenv("ENVIRONMENT") == "test":
            return None
        print(f"[AI_SERVICE NOTICE] Primary model failed ({e_prim}), checking fallback models...")
        if api_key:
            for alt_name in ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest"]:
                try:
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    alt_chat = ChatGoogleGenerativeAI(api_key=api_key, model=alt_name, temperature=0.6, max_retries=1, timeout=10)
                    res = alt_chat.invoke([HumanMessage(content=prompt_content)])
                    if res and hasattr(res, "content"):
                        txt = _extract_text(res.content)
                        if txt:
                            return txt
                except Exception:
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


def generate_dynamic_question(resume_text, previous_questions=None, question_index=1, last_score=None, last_answer=None, category=None, difficulty=None, responses=None, chat_model=None, candidate_name="Candidate"):
    previous_questions = previous_questions or []
    responses = responses or []
    is_no_resume = bool(resume_text and ("No Resume Provided" in resume_text or "JOB DESCRIPTION" in resume_text or "JOB PROFILE" in resume_text))
    stage_name = get_current_stage(question_index)
    ai_name = AI_INTERVIEWER["name"]

    # 1. Turn 1 GUARANTEE: Always start with a warm greeting and casual icebreaker!
    if question_index == 1:
        first_name = candidate_name.strip().split()[0] if candidate_name and candidate_name.strip() and candidate_name.lower() != "candidate" else ""
        name_str = f" {first_name}" if first_name else ""
        greeting = f"Hi{name_str}! I'm Ava, your AI interviewer today. It's really wonderful to meet you! Before we dive into technical questions, how are you feeling today and how is your day going so far?"
        return greeting, "Phase 1: Greeting & Icebreaker", False

    # 2. Handle Voice / Text Commands (Repeat & Hint)
    if last_answer and last_answer.strip().lower() in ["repeat", "can you repeat the question", "pardon"]:
        if previous_questions:
            return previous_questions[-1], "Repeat", False

    # Build conversation history Q&A string
    history_lines = []
    for idx, q in enumerate(previous_questions):
        ans = responses[idx] if idx < len(responses) else (last_answer if idx == len(previous_questions)-1 else "")
        history_lines.append(f"Turn {idx+1} Q: {q}\nTurn {idx+1} Candidate A: {ans if ans else '[Pending]'}")
    conv_history_str = "\n\n".join(history_lines) if history_lines else "None (Initial Turn)"

    cat_clean = (category or "").upper()
    if "HR" in cat_clean or "BEHAVIORAL" in cat_clean:
        track_instruction = """TRACK: HR & BEHAVIORAL INTERVIEW
STRICT MANDATE: Ask EXCLUSIVELY behavioral, leadership, teamwork, conflict resolution, situational judgment, and STAR-method questions (Situation, Task, Action, Result). DO NOT ask technical coding or syntax questions."""
    elif "DSA" in cat_clean or "ALGORITHM" in cat_clean:
        track_instruction = """TRACK: DATA STRUCTURES & ALGORITHMS (DSA)
STRICT MANDATE: Ask questions on data structures (Arrays, Binary Trees, Graphs, Hash Maps, Dynamic Programming), Big-O time/space complexity, and algorithmic trade-offs."""
    elif "SYSTEM" in cat_clean or "DESIGN" in cat_clean:
        track_instruction = """TRACK: SYSTEM DESIGN & ARCHITECTURE
STRICT MANDATE: Ask questions on distributed systems, microservices, database sharding/indexing, load balancers, caching (Redis), message queues (Kafka), and high availability."""
    elif "FUNDAMENTAL" in cat_clean or "CS" in cat_clean or "CORE" in cat_clean:
        track_instruction = """TRACK: CS FUNDAMENTALS
STRICT MANDATE: Ask questions on core CS pillars: Operating Systems (processes vs threads), Computer Networks (TCP/UDP, DNS), DBMS (ACID, indexing), and OOPS concepts."""
    elif "MAANG" in cat_clean or "BIG TECH" in cat_clean:
        track_instruction = """TRACK: MAANG / BIG TECH SCREENING
STRICT MANDATE: Ask high-bar algorithmic edge cases, production outage handling, system resilience, and deep engineering trade-off questions expected at Big Tech companies."""
    elif "GUESTIMATE" in cat_clean:
        track_instruction = """TRACK: GUESTIMATE & ESTIMATION
STRICT MANDATE: Ask a market-sizing or volume estimation problem. Evaluate structured top-down or bottom-up breakdown, realistic assumptions, and verbal articulation out loud."""
    elif "PUZZLE" in cat_clean or "LOGIC" in cat_clean:
        track_instruction = """TRACK: LOGIC PUZZLES
STRICT MANDATE: Ask a classic analytical/logic puzzle. Evaluate logical deduction, test case formulation, and ability to communicate thoughts step-by-step without skipping assumptions."""
    else:
        track_instruction = """TRACK: RESUME BASED TECHNICAL INTERVIEW
STRICT MANDATE: Ask questions directly tied to candidate's past projects, achievements, employment history, and specific tech stack listed in their resume."""

    # Strict Topic & Track Alignment (No Hallucinations)
    if is_no_resume:
        track_instruction = f'''TRACK: JOB DESCRIPTION SPECIFIC TECHNICAL INTERVIEW
STRICT MANDATE: Every question from Turn 2 onwards MUST be strictly and directly based on the provided Job Description and Target Role:
{resume_text[:2500]}
DO NOT ask questions on unrelated tools or technologies. Focus deeply on the exact skills, tech stack, and responsibilities demanded in the Job Description.'''
        if question_index == 1:
            phase_guidance = f'PHASE: GREETING & CASUAL ICEBREAKER. Say a warm welcome to the candidate using their name ({candidate_name}), introduce yourself as Ava (AI Recruiter), and ask a casual, low-stakes icebreaker question. STRICT MANDATE: DO NOT ask any technical questions on this first turn. Keep it friendly and welcoming.'
        elif question_index >= 10:
            phase_guidance = f"PHASE: CLOSING RETROSPECTIVE. Previous Candidate Answer: '{last_answer}'. Acknowledge candidate responses and close warmly."
        else:
            phase_guidance = f"PHASE: TARGET JOB DESCRIPTION ROUND (Turn {question_index}). Previous Candidate Answer: '{last_answer}'. React briefly (1 sentence), then ask a targeted technical question STRICTLY based on the requirements, tools, and architecture in the Job Description."
    elif 'DSA' in cat_clean or 'ALGORITHM' in cat_clean:
        if question_index == 1:
            phase_guidance = f'PHASE: GREETING & CASUAL ICEBREAKER. Say a warm welcome to the candidate ({candidate_name}), introduce yourself as Ava, and ask a casual icebreaker. DO NOT ask technical questions on Turn 1.'
        elif question_index == 2:
            phase_guidance = f"PHASE: DSA CODING PROBLEM 1. Previous Candidate Answer: '{last_answer}'. Briefly acknowledge, then present a concrete Data Structures & Algorithms problem (Arrays, Strings, Hash Maps, or Two Pointers). Ask the candidate to explain their high-level approach and time/space complexity."
        elif question_index == 3:
            phase_guidance = f"PHASE: DSA FOLLOW-UP & OPTIMIZATION. Previous Candidate Answer: '{last_answer}'. Probe on edge cases, memory constraints, or optimizing from O(N^2) to O(N log N) or O(N)."
        elif question_index == 4:
            phase_guidance = f"PHASE: DSA CODING PROBLEM 2. Previous Candidate Answer: '{last_answer}'. Present a problem on Trees, Graphs, or Dynamic Programming/Recursion. Ask the candidate to walk through their algorithm step-by-step."
        elif question_index == 5:
            phase_guidance = f"PHASE: DSA TRADEOFFS & COMPLEXITY. Previous Candidate Answer: '{last_answer}'. Probe the worst-case time and space complexity, recursion stack depth, and data structure trade-offs."
        elif question_index >= 10:
            phase_guidance = f"PHASE: CLOSING RETROSPECTIVE. Previous Candidate Answer: '{last_answer}'. Acknowledge candidate responses and close warmly."
        else:
            phase_guidance = f"PHASE: ADVANCED DSA SCENARIO (Turn {question_index}). Previous Candidate Answer: '{last_answer}'. Ask a sharp DSA scenario testing algorithmic reasoning and complexity."
    elif 'SYSTEM' in cat_clean or 'DESIGN' in cat_clean:
        if question_index == 1:
            phase_guidance = f'PHASE: GREETING & CASUAL ICEBREAKER. Say a warm welcome to the candidate ({candidate_name}), introduce yourself as Ava, and ask a casual icebreaker. DO NOT ask technical questions on Turn 1.'
        elif question_index == 2:
            phase_guidance = f"PHASE: SYSTEM DESIGN ARCHITECTURE. Previous Candidate Answer: '{last_answer}'. Briefly acknowledge, then present a core System Design challenge (e.g., Design a Distributed Rate Limiter, URL Shortener, or Notification System). Ask the candidate for functional/non-functional requirements and high-level component architecture."
        elif question_index == 3:
            phase_guidance = f"PHASE: DATA MODEL & STORAGE SCALING. Previous Candidate Answer: '{last_answer}'. Probe on database selection (SQL vs NoSQL), schema design, indexing, and data sharding/replication."
        elif question_index == 4:
            phase_guidance = f"PHASE: CACHING & PERFORMANCE. Previous Candidate Answer: '{last_answer}'. Ask about caching strategies (Redis/Memcached, eviction policies, cache stampede mitigation)."
        elif question_index == 5:
            phase_guidance = f"PHASE: HIGH AVAILABILITY & RESILIENCE. Previous Candidate Answer: '{last_answer}'. Probe on fault tolerance, circuit breakers, load balancing, and handling node crashes."
        elif question_index >= 10:
            phase_guidance = f"PHASE: CLOSING RETROSPECTIVE. Previous Candidate Answer: '{last_answer}'. Acknowledge candidate responses and close warmly."
        else:
            phase_guidance = f"PHASE: DISTRIBUTED SYSTEMS DEEP DIVE (Turn {question_index}). Previous Candidate Answer: '{last_answer}'. Probe message queues, eventual consistency, or microservice boundaries."
    elif 'FUNDAMENTAL' in cat_clean or 'CS' in cat_clean or 'CORE' in cat_clean:
        if question_index == 1:
            phase_guidance = f'PHASE: GREETING & CASUAL ICEBREAKER. Warm welcome from Ava. Casual icebreaker only.'
        elif question_index == 2:
            phase_guidance = f"PHASE: OPERATING SYSTEMS & CONCURRENCY. Previous Candidate Answer: '{last_answer}'. Ask a concrete OS question: processes vs threads, virtual memory, context switching, or race conditions and mutexes."
        elif question_index == 3:
            phase_guidance = f"PHASE: COMPUTER NETWORKS. Previous Candidate Answer: '{last_answer}'. Ask about TCP vs UDP, HTTP/HTTPS handshake, DNS resolution, or REST vs WebSocket protocols."
        elif question_index == 4:
            phase_guidance = f"PHASE: DATABASE MANAGEMENT SYSTEMS (DBMS). Previous Candidate Answer: '{last_answer}'. Ask about ACID transactions, B-Tree indexes, isolation levels, or SQL query optimization."
        elif question_index >= 10:
            phase_guidance = f"PHASE: CLOSING RETROSPECTIVE. Previous Candidate Answer: '{last_answer}'. Acknowledge candidate responses and close warmly."
        else:
            phase_guidance = f"PHASE: CS CORE PILLARS (Turn {question_index}). Previous Candidate Answer: '{last_answer}'. Ask about OOP design principles (SOLID), memory management, or distributed primitives."
    elif 'HR' in cat_clean or 'BEHAVIORAL' in cat_clean:
        if question_index == 1:
            phase_guidance = f'PHASE: GREETING & CASUAL ICEBREAKER. Warm welcome from Ava. Casual icebreaker only.'
        elif question_index >= 10:
            phase_guidance = f"PHASE: CLOSING RETROSPECTIVE. Previous Candidate Answer: '{last_answer}'. Acknowledge candidate responses and close warmly."
        else:
            phase_guidance = f"PHASE: BEHAVIORAL STAR SCENARIO (Turn {question_index}). Previous Candidate Answer: '{last_answer}'. Ask a targeted behavioral question using the STAR method: handling conflicting requirements, navigating disagreements, leading a project, or overcoming failure."
    else:
        if question_index == 1:
            phase_guidance = f'PHASE: GREETING & CASUAL ICEBREAKER. Warm welcome to {candidate_name} from Ava. Ask a low-stakes icebreaker. No technical questions on Turn 1.'
        elif question_index == 2:
            phase_guidance = f"PHASE: RESUME BACKGROUND. Previous Candidate Answer: '{last_answer}'. Ask about their core engineering background and primary tech stack from their resume."
        elif question_index == 3:
            phase_guidance = f"PHASE: RESUME PROJECT DEEP DIVE. Previous Candidate Answer: '{last_answer}'. Dive into a specific project listed on their resume, asking them to describe the problem, architecture, and their personal contribution."
        elif question_index == 4:
            phase_guidance = f"PHASE: TECHNICAL ARCHITECTURE & DECISIONS. Previous Candidate Answer: '{last_answer}'. Probe architectural decisions, libraries/tools used, and trade-offs on that project."
        elif question_index >= 10:
            phase_guidance = f"PHASE: CLOSING RETROSPECTIVE. Previous Candidate Answer: '{last_answer}'. Acknowledge candidate responses and close warmly."
        else:
            phase_guidance = f"PHASE: RESUME TECHNICAL ROUND (Turn {question_index}). Previous Candidate Answer: '{last_answer}'. Ask a targeted technical question directly tied to technologies on their resume."

    resume_has_text = bool(resume_text and not is_no_resume)
    system_prompt = build_ava_system_prompt(
        role=category or "Software Engineer",
        track=category or "Resume Based",
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

CRITICAL ANTI-REPETITION MANDATE:
- You MUST NOT repeat, rephrase, or ask about the same topic, technology, or scenario as any question in PREVIOUSLY ASKED QUESTIONS.
- Every question MUST explore a completely fresh angle, skill, or project from the candidate's background.

Return ONLY valid JSON with no markdown codeblock wrapping:
{{
  "acknowledgment": "<1 short sentence reacting to their previous answer, or empty string if first question>",
  "message": "<what Ava actually says out loud this turn — acknowledgment + question combined into natural speech>",
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

        if raw_output.startswith("```"):
            lines = raw_output.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_output = "\n".join(lines).strip()

        q_text = ""
        try:
            parsed = json.loads(raw_output)
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except Exception:
                    pass
            if isinstance(parsed, dict):
                msg = parsed.get("message", "").strip()
                ack = parsed.get("acknowledgment", "").strip()
                q_text = msg if msg else ack
                if parsed.get("stage"):
                    stage_name = parsed["stage"]
                needs_followup = bool(parsed.get("is_followup"))
            else:
                q_text = str(parsed)
        except Exception:
            import re
            msg_match = re.search(r'"message"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', raw_output)
            if msg_match:
                q_text = msg_match.group(1).replace('\\"', '"').replace('\\n', ' ').strip()
            else:
                q_text = raw_output

        if q_text.startswith('{') and '"message"' in q_text:
            import re
            msg_match = re.search(r'"message"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', q_text)
            if msg_match:
                q_text = msg_match.group(1).replace('\\"', '"').replace('\\n', ' ').strip()

        if (q_text.startswith('"') and q_text.endswith('"')) or (q_text.startswith("'") and q_text.endswith("'")):
            q_text = q_text[1:-1].strip()

        # Check for exact or semantic duplicate question
        if is_semantically_repetitive(q_text, previous_questions):
            raise ValueError(f"Duplicate or overly similar question generated by LLM: {q_text}")

        return q_text, stage_name, needs_followup
    except Exception as e:
        print(f"Dynamic question generation notice ({e}), selecting phase-appropriate question:")

        if question_index == 1:
            fallback_choice = random.choice(PHASE_1_GREETINGS)
        elif question_index == 2:
            fallback_choice = random.choice(PHASE_2_ICEBREAKERS)
        elif question_index == 3:
            fallback_choice = random.choice(PHASE_3_TRANSITIONS)
        else:
            # Pick non-repeating track-appropriate fallback
            if "HR" in cat_clean or "BEHAVIORAL" in cat_clean:
                track_fallbacks = [
                    "Tell me about a situation where you had a disagreement with a teammate or project lead. How did you resolve it?",
                    "Describe a time when a project deadline was unexpectedly moved up. How did you prioritize and deliver?",
                    "Tell me about a time when you received constructive feedback. What steps did you take to improve?"
                ]
            elif "DSA" in cat_clean or "ALGORITHM" in cat_clean:
                track_fallbacks = [
                    "How would you design a data structure that supports insert, delete, and getRandom in O(1) time complexity?",
                    "Explain how you would detect a cycle in a directed graph or linked list, and what space complexity it requires.",
                    "Compare Dynamic Programming and Greedy approaches — when would a greedy choice fail for an optimization problem?"
                ]
            elif "SYSTEM" in cat_clean or "DESIGN" in cat_clean:
                track_fallbacks = [
                    "How would you design a scalable rate limiting service for an API handling 100k requests per second?",
                    "Explain database sharding vs partitioning, and how you prevent hot spots in distributed storage.",
                    "How do message queues like Kafka ensure message ordering and fault tolerance in microservices?"
                ]
            elif "FUNDAMENTAL" in cat_clean or "CS" in cat_clean or "CORE" in cat_clean:
                track_fallbacks = [
                    "What is the difference between a process and a thread, and how does the OS handle context switching?",
                    "Explain the difference between TCP and UDP, and why video streaming might prefer one over the other.",
                    "What are the ACID properties in database transactions, and how does Isolation prevent race conditions?"
                ]
            elif "MAANG" in cat_clean or "BIG TECH" in cat_clean:
                track_fallbacks = [
                    "How would you design a globally distributed cache with sub-millisecond latency and multi-region consistency?",
                    "Describe how you would diagnose and mitigate a cascading failure in a microservices ecosystem during peak load."
                ]
            else:
                track_fallbacks = [
                    "Tell me about the most complex technical project you've worked on, and the architectural trade-offs you made.",
                    "Looking back at your recent projects, what is one design decision you would implement differently today?"
                ]

            available = [q for q in track_fallbacks if not is_semantically_repetitive(q, previous_questions)]
            fallback_choice = random.choice(available) if available else track_fallbacks[0]
            
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
