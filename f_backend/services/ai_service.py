import random
from langchain_core.messages import HumanMessage
from services.ai_config import AI_INTERVIEWER, AVA_SYSTEM_PROMPT, build_ava_system_prompt

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

def generate_dynamic_question(resume_text, previous_questions=None, question_index=1, last_score=None, last_answer=None, category=None, difficulty=None, responses=None, chat_model=None):
    previous_questions = previous_questions or []
    responses = responses or []
    is_no_resume = resume_text.startswith("JOB PROFILE DETAILS (No Resume Provided):")
    stage_name = get_current_stage(question_index)
    ai_name = AI_INTERVIEWER["name"]

    # 1. Handle Voice / Text Commands (Repeat & Hint)
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
    else:
        track_instruction = """TRACK: RESUME BASED TECHNICAL INTERVIEW
STRICT MANDATE: Ask questions directly tied to candidate's past projects, achievements, employment history, and specific tech stack listed in their resume."""

    if question_index == 1:
        if "HR" in cat_clean or "BEHAVIORAL" in cat_clean:
            phase_guidance = "PHASE: GREETING & HR QUESTION 1. Give Ava's warm greeting (1-2 sentences), then ask an impactful STAR behavioral question."
        elif "DSA" in cat_clean or "ALGORITHM" in cat_clean:
            phase_guidance = "PHASE: GREETING & DSA QUESTION 1. Give Ava's warm greeting (1-2 sentences), then present a specific Data Structures or Algorithmic problem."
        elif "SYSTEM" in cat_clean or "DESIGN" in cat_clean:
            phase_guidance = "PHASE: GREETING & SYSTEM DESIGN QUESTION 1. Give Ava's warm greeting (1-2 sentences), then present a System Design scenario."
        else:
            phase_guidance = "PHASE: GREETING & TECHNICAL QUESTION 1. Give Ava's warm greeting (1-2 sentences), then ask about their background or key project."
    elif question_index == 2:
        phase_guidance = f"PHASE: RESUME & PROJECT DEEP DIVE. Previous Candidate Answer: '{last_answer}'. Briefly acknowledge what they said, then probe deeper into their technical/project choices."
    elif question_index >= 5:
        phase_guidance = f"PHASE: CLOSING / FINAL QUESTION. Previous Candidate Answer: '{last_answer}'. Briefly acknowledge, then transition towards closing or final high-level question."
    else:
        phase_guidance = f"PHASE: CORE ROUND (Turn {question_index}). Previous Candidate Answer: '{last_answer}'. Briefly acknowledge their answer, then ask ONE sharp question following the TRACK MANDATE."

    resume_has_text = bool(resume_text and not is_no_resume)
    system_prompt = build_ava_system_prompt(
        role=category or "Software Engineer",
        track=category or "Resume Based",
        difficulty=difficulty or "Medium",
        experience_level="1-3 Years",
        duration_minutes=20,
        resume_provided=resume_has_text,
        resume_data=resume_text[:2000] if resume_has_text else "None",
        candidate_name="Candidate"
    )

    prompt = f"""{system_prompt}

DYNAMIC CONTEXT DATA FOR THIS TURN:
- conversation_history:
{conv_history_str}

LATEST CANDIDATE RESPONSE:
"{last_answer or 'None'}"

{track_instruction}
{phase_guidance}

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
        response = chat_model.invoke([HumanMessage(content=prompt)])
        raw_output = response.content.strip()

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

        # Check for duplicate question
        if q_text in previous_questions:
            raise ValueError("Duplicate question generated by LLM")

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

            available = [q for q in track_fallbacks if q not in previous_questions]
            fallback_choice = random.choice(available) if available else track_fallbacks[0]
            
        return fallback_choice, stage_name, False

def generate_hint(question, resume_text, chat_model):
    ai_name = AI_INTERVIEWER["name"]
    prompt = f"""You are {ai_name}, a supportive and professional AI interviewer. The candidate asked for a hint on this question:
Question: {question}
Candidate Profile/Resume: {resume_text[:1000]}

Provide a small, helpful, 1-2 sentence hint that guides their thought process without giving away the complete answer directly."""
    try:
        response = chat_model.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as e:
        print(f"Generate hint error: {e}")
        return "Focus on breaking the problem down into core components and using the STAR framework (Situation, Task, Action, Result)."
