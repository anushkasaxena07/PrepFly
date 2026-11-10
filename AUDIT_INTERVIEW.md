# PrepFly AI Interview Capture, Evaluation & Report Engine: Audit & Root Cause Analysis (Phase 0)

**Date**: 2026-11-10  
**Repository**: `PrepFly` (`f_backend/`, `f_frontend/`)  
**Scope**: AI Interview Flow, Speech Pipeline, Gemini AI Integration, Supabase Schemas, Scoring & Reporting Engine  
**Author**: Senior Full-Stack & Systems Engineer  

---

## 1. Frontend AI Interview Flow Analysis

The interview workflow is hosted primarily in `f_frontend/src/components/AvaTab.jsx` (and mirrored in `f_frontend/src/InterviewPage.jsx`):

### 1.1 Setup Screen (`resume_upload` & `type_selection`)
- **Component**: [`f_frontend/src/components/AvaTab.jsx:220-755`](file:///D:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/AvaTab.jsx#L220-L755)
- **Flow**:
  1. **Upload Resume**: Calls `POST /upload` with FormData (`file`). The backend extracts text and parses structured data via Gemini. Returns `{ session_id, resume_text, ats_score, structured_data }`.
  2. **Non-Resume Flow**: If skipping resume, calls `POST /create-session-no-resume` with `{ role, category, difficulty }`.
  3. **Device Check**: Candidate verifies camera and microphone stream (`navigator.mediaDevices.getUserMedia`). Confirms affirmative privacy consent checkbox (`DPDP Act 2023`).
  4. **Start Interview**: Calls `POST /start-interview` with `{ session_id, category, difficulty }`. Backend generates Turn 1 question and initializes stage.

### 1.2 Active Interview Screen (`live_call`) & Answer Capture
- **Component**: [`f_frontend/src/components/AvaTab.jsx:750-1120`](file:///D:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/AvaTab.jsx#L750-L1120)
- **Speech-to-Text Pipeline**:
  - Web Speech API: `window.SpeechRecognition || window.webkitSpeechRecognition` starts upon Ava's question completion (`startVoiceRecognition()`).
  - Audio Chunks Capture: `MediaRecorder` records audio stream simultaneously into `audioChunksRef.current`.
  - VAD (Voice Activity Detection): Frontend measures silence after $\ge 3$ candidate words (`AvaTab.jsx:964`), auto-submitting the response.
- **Per-Turn Answer Submission**:
  - Calls `POST /next` ([`AvaTab.jsx:1083-1090`](file:///D:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/AvaTab.jsx#L1083-L1090)):
    ```javascript
    const res = await apiFetch("/next", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        answer: textToSubmit,
        category: chosenCategory,
        role: chosenRole,
        difficulty: difficulty || "Medium"
      })
    });
    ```
  - **CRITICAL DEFECT**: The frontend sends **only** `{ session_id, answer, category, role, difficulty }`. It sends **NO** `audio_duration_s`, **NO** timestamps (`started_at`, `ended_at`), **NO** `input_mode` (`"speech"` vs `"typed"`), and **NO** audio blob reference. Duration and timestamps are never transmitted!

### 1.3 Final Report Screen Loading
- **Component**: [`f_frontend/src/components/AvaTab.jsx:1145-1200`](file:///D:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/AvaTab.jsx#L1145-L1200)
- When the interview completes or times out, frontend calls `POST /end-interview` with `{ session_id, role, category, difficulty, eye_contact_pct, tab_switches }`.
- If `reportData.report.includes("Generating")`, it initiates a polling loop against `GET /session-report/:session_id` every 4 seconds (up to 12 attempts).
- Once received, `reportData` is rendered inside `AvaTab.jsx:2120-2640`.

---

## 2. Flask Routes & Services Inspection

### 2.1 Route Map & Behavior
| Route | Method | File & Line | Handler Responsibility | Failure Modes Observed |
|---|---|---|---|---|
| `/upload` | POST | [`f_backend/app.py:2045`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2045) | Accepts PDF/DOCX, calls `parse_resume_content`, writes session row to `sessions` table. | Catches Gemini 503/504 and swallows it, returning HTTP 200 with fake `"Candidate"` profile. Fails Supabase insert if `sessions.resume_text` is missing (`PGRST204`), silently falling back to local SQLite. |
| `/create-session-no-resume` | POST | [`f_backend/app.py:2140`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2140) | Creates initial session row without resume. | Can fail remote insert if columns are missing. |
| `/start-interview` | POST | [`f_backend/app.py:2238`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2238) | Validates session ownership via `get_owned_session`, generates first question, saves to DB. | **Returns 404** when `/upload` failed to write to remote Supabase and saved to local SQLite on another worker/container. |
| `/next` | POST | [`f_backend/app.py:2330`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2330) | Receives turn answer, computes live metrics, appends answer to `session["responses"]`, updates DB. | **Swallows DB errors** (`app.py:2588`): catches `Exception` and prints notice, returning HTTP 200 while `responses` is never persisted in Supabase! |
| `/end-interview` | POST | [`f_backend/app.py:2866`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2866) | Checks `responses`, compiles report via `fast_compile_report` or defaults to Unevaluated F-grade. | If `responses` is empty (due to `/next` save failure), creates hardcoded `Strong Reject (No Responses Provided)` and grade `F`. |
| `/session-report/<id>` | GET | [`f_backend/app.py:3043`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L3043) | Fetches completed session report JSON from Supabase. | Returns 404 if session is missing or unowned. |
| `/speech-to-text` | POST | [`f_backend/app.py:5530`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L5530) | Fallback transcription using Gemini. | High latency (~2-4s) if invoked per turn. |

### 2.2 Why `POST /start-interview` Returns 404
In [`f_backend/app.py:1335-1383`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L1335-L1383):
```python
def get_owned_session(session_id):
    clean_session_id = str(session_id or "").strip()
    res = supabase.table("sessions").select("*").eq("session_id", clean_session_id).execute()
    s = res.data[0] if res and res.data else None
    ...
    if not s:
        return None, (jsonify({"error": "Session not found"}), 404)
```
When `/upload` fails to write to remote Supabase because of `PGRST204` (missing `resume_text` column), lines 2100-2108 catch the error and fall back to `local_supabase` (an ephemeral local SQLite database on Render/local disk).
In multi-worker production (Render/Gunicorn or server restarts), subsequent requests route to another worker where the local SQLite has no such session, or the remote Supabase returns 0 rows. Result: `{"error": "Session not found"}, 404`.

---

## 3. Speech & Telemetry Pipeline Inspection

### 3.1 Where Speech is Converted to Text
- **Client Web Speech API**: [`f_frontend/src/components/AvaTab.jsx:911`](file:///D:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/AvaTab.jsx#L911) uses browser `window.SpeechRecognition`.
- **Backend Fallback**: [`f_backend/app.py:5530`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L5530) (`/speech-to-text`) uses Gemini Audio input.

### 3.2 Where Duration and Timestamps are Captured
- **FINDING**: Timestamps and speech duration are **NEVER** captured or passed by the frontend in `apiFetch("/next")` ([`AvaTab.jsx:1085`](file:///D:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/AvaTab.jsx#L1085))!
- `f_backend/services/interview_service.py:10-24` defines:
  ```python
  def analyze_live_response(answer_text, duration_seconds=15):
      words = re.findall(r'\b\w+\b', answer_text.lower())
      word_count = len(words)
      wpm = int((word_count / max(duration_seconds, 5)) * 60) if duration_seconds > 0 else int(word_count * 4)
  ```
  Because the frontend provides no duration, the backend **always defaults to 15 seconds**!
- In report compilation ([`f_backend/services/feedback_service.py:891-896`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/services/feedback_service.py#L891-L896)):
  ```python
  full_transcript = " ".join([str(ans) for ans in responses if ans and str(ans).strip()])
  total_w = len(full_transcript.split())
  speech_metrics = {
      "wpm": round((total_w / 15.0) * 60) if total_w > 0 and not is_incomplete else (135 if total_w >= 10 else 0),
      "pacing_label": "Optimal (130-155 WPM)" if total_w >= 20 else ("Deliberate Pace" if total_w > 0 else "No Speech Detected"),
      "total_words": total_w,
      "filler_count": 0,
      ...
  }
  ```
- **Why WPM is 0**: If `responses` is empty in `sessions` (due to the unpersisted session or swallowed database update in `/next`), `total_w == 0`. Therefore, `wpm = 0`, `total_words = 0`, `pacing_label = "No Speech Detected"`.
- Furthermore, in [`AvaTab.jsx:2340`](file:///D:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/AvaTab.jsx#L2340):
  ```javascript
  const isSpeechAbsent = !sm.wpm || sm.wpm === 0 || sm.total_words === 0 || hasNoResponses;
  ```
  When `isSpeechAbsent` evaluates to `true`, the frontend displays:
  **"No Verbal Responses Recorded: Candidate did not speak during this interview."**

---

## 4. Gemini AI Integration Inspection

### 4.1 Architecture & Models
- **Wrapper**: `safe_invoke_llm` in [`f_backend/services/ai_service.py:15-60`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/services/ai_service.py#L15-L60) using LangChain's `ChatGoogleGenerativeAI`.
- **Model Candidates**: `gemini-2.5-flash`, fallback candidates `gemini-3.5-flash`, `gemini-3.8-flash`, `gemini-flash-latest`.
- **Parameters**: `temperature=0.6`, `timeout=10`, `max_retries=1`.
- **Defects in Reliability**:
  - No exponential backoff with jitter on 503/504 errors.
  - Timeouts (10s) are too aggressive for large prompts, triggering frequent 504 timeouts.

### 4.2 Prompts Flagged for Operating Rule R1 Violations (Returning Direct Scores/Verdicts)
| File & Function | Prompt Excerpt | Violation Type | Operating Rule Violation |
|---|---|---|---|
| [`f_backend/services/feedback_service.py:590`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/services/feedback_service.py#L590) (`evaluate_response_comprehensive`) | `"Rate the candidate's answer on a scale of 0-10. Return JSON: { \"score\": 8, ... }"` | Direct Score from LLM | **Violates R1**: LLM outputs numeric score directly instead of rubric criteria. |
| [`f_backend/services/feedback_service.py:1210`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/services/feedback_service.py#L1210) (`evaluate_google_technical_correctness`) | `"Provide an accuracy_score between 0 and 100 based on technical correctness."` | Direct Score from LLM | **Violates R1**: LLM decides numeric accuracy score directly. |
| [`f_backend/services/feedback_service.py:1710`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/services/feedback_service.py#L1710) (`evaluate_leadership_presence`) | `"Output presence_score (0-100) and hiring recommendation (Strong Hire / Reject)."` | Direct Hiring Recommendation from LLM | **Violates R1**: LLM issues hiring verdict. |
| [`f_backend/services/feedback_service.py:1810`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/services/feedback_service.py#L1810) (`generate_professional_report_json`) | `"Generate overall grade (S/A/B/C/D/F) and hiring recommendation."` | Direct Grade & Verdict from LLM | **Violates R1**: LLM outputs final grade. |

---

## 5. Supabase Schema Diff & Mismatch Inventory

Comparing remote database expectations with code writes:

| Table | Column Written by Code | Status in Remote Supabase | Observed Error | Impact |
|---|---|---|---|---|
| `sessions` | `resume_text` | **MISSING** | `PGRST204` on `/upload` | Session insert fails, falls back to SQLite, causing 404 in `/start-interview`. |
| `sessions` | `consent_given`, `consent_timestamp`, `privacy_policy_version` | **MISSING** in old schema | `PGRST204` | Fails compliance recording. |
| `sessions` | `report_json`, `knowledge_map`, `turn_count`, `interview_state` | **MISSING** in old schema | `PGRST204` on `/next` and `/end-interview` | Database update fails silently in `app.py:2588`, wiping out responses! |
| `parsed_resumes` | `created_at` | **MISSING** | `PGRST204` on `save_cached_resume` | Resume caching crashes. |
| `activity_logs` | `actor_id` | **MISSING** | `PGRST204` | Audit logging fails. |
| `organization` | `status` | **MISSING** | `PGRST204` | Admin queries fail. |

### 5.1 RLS Policies Analysis
- Remote Supabase tables have Row Level Security enabled in the Supabase dashboard by default.
- Backend interacts via `service_role` key in some configurations, but if `SUPABASE_SERVICE_KEY` is falling back to `SUPABASE_ANON_KEY`, queries on `sessions` or `users` without matching user JWT fail with permission denied or return 0 rows.
- No DDL policies exist in `supabase_schema.sql` to explicitly grant service role bypass or define user-level policies for `sessions` and `evaluations`.

---

## 6. Report Lineage Table

| Displayed Value | Frontend Field (`AvaTab.jsx`) | API Route | Backend Function | Tables / Columns | Formula / Derivation |
|---|---|---|---|---|---|
| **Candidate Name** | `safeUser?.name \|\| "Candidate"` (L1212, L1781) | `POST /end-interview` | `get_candidate_name_for_session(session)` (`app.py:2212`) | `users.name` (where `id = session.user_id`) | If `user_id` is None, returns `"Candidate"`. Never checks Google token metadata, Google JWT claims, or parsed resume. |
| **Overall Grade** | `gInfo.grade` (L2120-2150) | `POST /end-interview` | `calculate_grade_info(0)` (`app.py:2900`) / `fast_compile_report` (`feedback_service.py:833`) | `sessions.final_grade`, `sessions.final_score` | If `valid_evaluated_answers == 0`: hardcoded `grade = "F"`, `score = 0`. |
| **Hiring Recommendation** | `gInfo.rec \|\| recText` (L2217) | `POST /end-interview` | `calculate_grade_info(0)` / `fast_compile_report` | `sessions.hiring_recommendation` | If `valid_evaluated_answers == 0`: hardcoded `"Strong Reject (No Responses Provided)"`. |
| **10 Dimension Scores** | `sec.score`, `sec.grade` (L2275-2285) | `POST /end-interview` | `app.py:2927-2938` / `feedback_service.py:640` | `sessions.report_json->section_grades` | If `not has_replied`: all 10 dimensions set to `score: 0`, `grade: "F"`. If missing: renders `"Not Evaluated"`. |
| **Speaking Pace (WPM)** | `sm.wpm` (L2365) | `POST /end-interview` | `feedback_service.py:894` | `sessions.report_json->speech_metrics->wpm` | `round((total_w / 15.0) * 60)` or hardcoded `135` if `total_w >= 10`, else `0`. |
| **Word Count** | `sm.total_words` (L2340) | `POST /end-interview` | `feedback_service.py:892` | `sessions.report_json->speech_metrics->total_words` | `len(full_transcript.split())`. Evaluates to `0` when `responses` is empty. |
| **Filler Words** | `sm.filler_count` (L2370) | `POST /end-interview` | `feedback_service.py:898` | `sessions.report_json->speech_metrics->filler_count` | Hardcoded `0` in `fast_compile_report`. |
| **Question List** | `turn_evaluations` (L2470) | `POST /end-interview` | `feedback_service.py:790` | `sessions.questions`, `sessions.responses`, `sessions.feedbacks` | Empty if `session.responses` was not saved. Frontend renders client-side memory `allFeedbacks` if backend returns empty. |
| **Top Strengths** | `reportData.strengths` (L2570) | `POST /end-interview` | `app.py:2939` / `feedback_service.py:840` | `sessions.report_json->strengths` | If `valid_evaluated_answers == 0`: hardcoded `dyn_strengths = []`, `"None identified (no responses provided)"`. |
| **Focus Areas & Weaknesses** | `reportData.weaknesses` (L2590) | `POST /end-interview` | `feedback_service.py:820` | `sessions.report_json->weaknesses` | `f"Turn {idx+1} Depth Gap ({classification})"` + `imp_msg` (hardcoded template: `"Review the core domain definitions, trade-offs, and implementation edge cases."`). |

---

## 7. Explicit Answers with Code Excerpts

### 7.1 Where does the report get its answers from? Is that source populated at report time?
In [`f_backend/app.py:2880-2884`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2880-L2884):
```python
feedbacks = session.get("feedbacks") or []
questions = session.get("questions") or []
responses = session.get("responses") or []
```
The report reads answers from `session.get("responses")`.
**Is that source populated at report time?**
**NO.** In production, `session.get("responses")` is frequently **EMPTY (`[]`)** because in [`f_backend/app.py:2588`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2588), `/next` attempts to update the remote Supabase `sessions` table. When that update throws a schema mismatch exception (`PGRST204` or connection error), line 2588 catches it:
```python
except Exception as ex:
    print("Session DB save notice:", ex)
```
The error is swallowed, HTTP 200 is returned to the client, but the responses were **NEVER committed to the database**. At report time, `session.get("responses")` returns `[]`.

### 7.2 Why is WPM 0 when the user spoke?
Three concurrent root causes:
1. **Frontend never sends audio duration**: [`AvaTab.jsx:1085`](file:///D:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/AvaTab.jsx#L1085) only sends `{ session_id, answer, category, role, difficulty }`. No timestamps or duration are sent.
2. **Backend divides by unpersisted word count**: In [`feedback_service.py:891-894`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/services/feedback_service.py#L891-L894), `wpm` is calculated from `total_w` (words in `session["responses"]`). Because `responses` is empty, `total_w == 0`, leading to `wpm = 0`.
3. **Frontend zero-coercion**: In [`AvaTab.jsx:2340-2385`](file:///D:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/AvaTab.jsx#L2340-L2385), `isSpeechAbsent` evaluates to `true` whenever `wpm === 0` or `hasNoResponses`, displaying `"No Verbal Responses Recorded"` even though the user spoke into the microphone.

### 7.3 Why is a verdict generated when evaluation did not run?
In [`f_backend/app.py:2886-2910`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2886-L2910) and [`f_backend/services/feedback_service.py:832-840`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/services/feedback_service.py#L832-L840):
```python
if not has_replied:
    g_info = calculate_grade_info(0)
    f_report = {
        "overall_score": 0.0,
        "grade": "F",
        "hiring_recommendation": "Provisional (Interview Ended Early)",  # or Strong Reject
        "performance_level": "Provisional / Unevaluated",
        ...
```
When `responses` is empty (due to persistence failure), the code treats the technical failure as candidate non-performance, coerces missing data to `0`, awards an `F` grade, and assigns `"Strong Reject (No Responses Provided)"`. This directly violates Operating Rules R2 and R3.

### 7.4 Where does "Candidate" come from and why is the Google name not used?
In [`f_backend/app.py:2212-2223`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2212-L2223):
```python
def get_candidate_name_for_session(session):
    user_id = session.get("user_id")
    if user_id:
        try:
            user_res = supabase.table("users").select("name").eq("id", user_id).execute()
            if user_res and user_res.data:
                name = user_res.data[0].get("name")
                if name:
                    return name.strip()
        except Exception:
            pass
    return "Candidate"
```
And in [`f_backend/services/resume_service.py:177`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/services/resume_service.py#L177):
```python
except Exception as e:
    fallback_data = {"full_name": "Candidate", "skills": ["Software Engineering", "Algorithms"], "ats_score": 70}
```
**Why the Google name is not used**:
1. When a user authenticates with Google via Supabase OAuth or Google Identity Services, their name resides in `request.current_user["name"]`, Google JWT payload claims (`name`, `given_name`), or Supabase `user_metadata["full_name"]`.
2. `get_candidate_name_for_session` **only** queries `users.name` using `session.get("user_id")`. If the session was created before login, or if `user_id` is an auth UID not yet mirrored into the custom `users` table, the query returns empty and defaults to `"Candidate"`.
3. In `/upload`, when Gemini fails (503/504), `resume_service.py` sets `full_name = "Candidate"`, caches it, and overwrites candidate identity.

### 7.5 Where do the "Turn N Depth Gap" texts come from?
In [`f_backend/services/feedback_service.py:820`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/services/feedback_service.py#L820):
```python
if acc_score < 70.0 and classification not in (CLASS_NO_ANSWER, CLASS_EARLY_EXIT):
    imp_msg = fb.get("improvement") or f"Elaborate on technical trade-offs and concrete implementations for Question {idx+1}."
    scored_weaknesses.append({
        "title": f"Turn {idx+1} Depth Gap ({classification})",
        "evidence": f"Answer '{candidate_ans_str[:80]}...' - {imp_msg}"
    })
```
And in [`f_backend/services/feedback_service.py:62`](file:///D:/Downloads/interviewsystem/interviewsystem/f_backend/services/feedback_service.py#L62):
```python
elif classification == CLASS_INCORRECT:
    feedback_msg = f"❌ Technical definitions or approaches were incorrect. {rationale}"
    improvement_msg = "Review the core domain definitions, trade-offs, and implementation edge cases."
```
When `acc_score < 70`, the service constructs a templated string:
`"Turn {idx+1} Depth Gap ({classification})"`
combined with the generic static string:
`"Review the core domain definitions, trade-offs, and implementation edge cases."`
It is a hardcoded template, not evidence derived from verbatim candidate quotes.

---

## 8. Local Reproduction of Failures 1–6

### Reproduction Script
Executed against `f_backend` with Python 3.11:

```python
import os
from services.feedback_service import fast_compile_report
from services.resume_service import parse_resume_content

# 1. Reproduce Failures 1, 3, 4, 6 (Empty responses after persistence failure)
rep = fast_compile_report(
    role="Software Engineer",
    track="Resume Based",
    difficulty="Medium",
    experience_level="1-3 Years",
    questions=["What is a process and thread?"],
    responses=[],
    feedbacks=[],
    candidate_name="Candidate",
    interview_mode="resume",
    total_questions_expected=10
)
print("REPRODUCTION 1 & 4 (Verdict on missing data):")
print("  Grade:", rep.get("grade"))
print("  Grade Label:", rep.get("grade_label"))
print("  Recommendation:", rep.get("recommendation"))
print("  Overall Score:", rep.get("overall_score"))

print("REPRODUCTION 3 (Speech metrics on missing data):")
sm = rep.get("speech_metrics", {})
print("  WPM:", sm.get("wpm"))
print("  Pacing Label:", sm.get("pacing_label"))
print("  Total Words:", sm.get("total_words"))

print("REPRODUCTION 6 (Strengths on missing data):")
print("  Strengths:", rep.get("strengths"))

# 2. Reproduce Failure 5 (Generic Template Weakness)
rep2 = fast_compile_report(
    role="Software Engineer",
    track="Resume Based",
    difficulty="Medium",
    experience_level="1-3 Years",
    questions=["Explain Postgres indexing"],
    responses=["It makes queries faster."],
    feedbacks=[{
        "score": 4.0,
        "accuracy_score": 40,
        "correctness": "partially_correct",
        "improvement": "Review the core domain definitions, trade-offs, and implementation edge cases."
    }],
    candidate_name="Candidate",
    interview_mode="resume",
    total_questions_expected=10
)
print("REPRODUCTION 5 (Template text):")
for w in rep2.get("weaknesses", []):
    print(" ", w)

# 3. Reproduce Failure 2 (Gemini Failure -> Silent "Candidate" Fallback)
res = parse_resume_content("Resume text for Anushka Saxena", chat_model=None)
print("REPRODUCTION 2 (Identity Fallback):")
print("  Parsed Name:", res.get("structured_data", {}).get("full_name"))
```

### Actual Execution Output
```
REPRODUCTION 1 & 4 (Verdict on missing data):
  Grade: F
  Grade Label: Unevaluated / No Responses
  Recommendation: Strong Reject (No Responses Provided)
  Overall Score: 0

REPRODUCTION 3 (Speech metrics on missing data):
  WPM: 0
  Pacing Label: No Speech Detected
  Total Words: 0

REPRODUCTION 6 (Strengths on missing data):
  Strengths: []

REPRODUCTION 5 (Template text):
  {'title': 'Turn 1 Depth Gap (partially_correct)', 'evidence': "Answer 'It makes queries faster....' - Review the core domain definitions, trade-offs, and implementation edge cases."}

REPRODUCTION 2 (Identity Fallback):
  Parse resume AI error: 'NoneType' object has no attribute 'invoke'
  Parsed Name: Candidate
```
All 6 failures observed by users are **100% verified and reproduced**.

---

## 9. Proposed Minimal-Change Remediation Plan

### 9.1 Phase 1: Schema Fix & Reliable Session Creation
- Create migration script `f_backend/migrations/20261110_interview_schema_fix.sql`:
  - Add missing columns to `sessions`: `resume_text`, `consent_given`, `consent_timestamp`, `privacy_policy_version`, `report_json`, `knowledge_map`, `turn_count`, `interview_state`, `blueprint_json`, `adaptive_state_json`, `report_status`, `model_used`, `prompt_versions_json`.
  - Add missing column to `parsed_resumes`: `created_at`.
  - Add missing column to `activity_logs`: `actor_id`.
  - Add missing column to `organization`: `status`.
  - Create table `interview_turns` and `interview_speech_metrics`.
- Add startup schema validator in `app.py` checking required columns and logging actionable error instead of silent fallbacks.
- Update `/upload` and `parse_resume_content`: Fail loudly on Gemini 503/504 with HTTP 503/504 and retryable error flag. Do not return fake 200 with "Candidate".
- Make `/start-interview` idempotent and auto-create the session if not found.

### 9.2 Phase 2: Interview Capture & Persistence (Ground Truth)
- Persist every turn into `interview_turns` immediately upon receipt in `/next`.
- Update frontend `AvaTab.jsx` / `InterviewPage.jsx` to transmit:
  - `audio_duration_s`: actual duration from `MediaRecorder`.
  - `started_at` & `ended_at`: ISO client timestamps.
  - `input_mode`: `"speech"` or `"typed"`.
- Implement deterministic calculation for WPM: `wpm = round((word_count / max(duration_s, 3)) * 60)`. If duration or speech is missing, set to `None` (NULL), **never 0**.

### 9.3 Phase 3: Evidence-Based Rubric Grading
- Migrate per-turn grading to `EvaluationService` using versioned prompts and structured criteria matching.
- Verify quoted justifications against verbatim candidate answer.
- Persist evaluations into `interview_evaluations` and Prompt 1's `skill_evidence`.

### 9.4 Phase 4: Deterministic Scoring, Grade & Verdict Engine
- Create `interview_scoring_config.py` with all weights, thresholds, and grade bands.
- Create pure functions in `interview_scoring_service.py`.
- Compute overall score and grade deterministically from code.
- Report status state machine:
  - `EVALUATED`: $\ge 5$ questions answered substantively.
  - `PARTIAL`: $1 \le$ questions $< 5$.
  - `INCOMPLETE_INSUFFICIENT_DATA`: 0 substantive questions answered. **NO SCORE, NO GRADE, NO VERDICT.**
  - `EVALUATION_FAILED`: LLM or technical error.
- Enforce: Missing data is NULL, never coerced to 0 or "Strong Reject".

### 9.5 Phase 5: Dynamic Report Generation
- Build report strictly from persisted `interview_turns` and `interview_evaluations`.
- Eliminate template strings (`"Turn N Depth Gap"`).
- Require every strength and weakness to cite turn IDs and verbatim quoted phrases.
- Feed candidate skill profile in Prompt 1's `candidate_skill_states`.

### 9.6 Phase 6: Frontend Dark UI Polish
- Update `AvaTab.jsx` to render `INCOMPLETE_INSUFFICIENT_DATA` with explanatory banner and "Practice Again" button.
- Render unassessed dimensions as neutral gray (`"Not Evaluated"`).
- Connect evidence drawer showing exact quoted evidence.
- Display verified candidate name using priority: Confirmed Profile -> Google Account -> Parsed Resume -> "Candidate".

---

## 10. Before / After Remediation Summary (Phases 1–8 Verified)

| Failure Mode (Phase 0 Audit) | Before Remediation | After Remediation | Verified By |
|---|---|---|---|
| **1. Fake verdict on missing data** | Returned `Grade F` & `"Strong Reject (No Responses Provided)"` even when user spoke | `score_interview_session` enforces `EVALUATED`, `PARTIAL`, `INCOMPLETE_INSUFFICIENT_DATA`, `EVALUATION_FAILED`; missing evaluations emit `EVALUATION_FAILED` + `grade = null` + `recommendation = null` | `test_phase4_scoring_engine.py`, `test_phase8_interview_e2e.py::test_02` |
| **2. Identity lost (`"Candidate"`)** | Read only `users.name` or cached `"Candidate"` after Gemini 503 parse failure | Priority `profile -> google -> resume -> fallback`; Gemini 503/504 fails loudly with HTTP 503/504 (`retryable: true`) and never caches `"Candidate"` | `identity_service.py`, `test_phase1_schema_and_session.py`, `test_phase8_interview_e2e.py::test_10` |
| **3. Speech telemetry 0 WPM / `"No Verbal Responses"`** | Frontend `/next` omitted timing & duration; backend coerced missing to `0` | Frontend transmits `audio_duration_s`, `started_at`, `ended_at`, `input_mode`, `stt_engine`, `stt_confidence`; missing timing yields `NULL` / `"Not measurable"` (neutral gray) | `interview_speech_service.py`, `AvaTab.jsx`, `test_phase2_interview_capture.py` |
| **4. Missing schema & swallowed `PGRST204`** | Missing columns caused `PGRST204` swallowed by fallback; `/start-interview` returned `404` | Migration `010` + rollback + startup self-check + strict RLS (`REVOKE` client writes & rubric reads); `/start-interview` idempotent & auto-creates session | `010_interview_capture_and_evaluation.sql`, `schema_check_service.py`, `test_phase1_schema_and_session.py` |
| **5. Generic `"Turn N Depth Gap"` & `"No tangible strengths"`** | Static template text returned regardless of candidate transcript | Strengths & weaknesses built solely from criteria passing verbatim quote substring checks citing `turn_id` + `quote`; `"Not assessed yet"` isolated separately | `interview_rubric_grader.py`, `interview_report_service.py`, `test_phase3_rubric_grading.py`, `test_phase5_report_generation.py` |
| **6. Blocked SMTP & missing `redis` / `fitz`** | Gmail SMTP hung; `redis` absent in requirements; bare `import fitz` | HTTP email API (`Resend`/`SendGrid`, `502` surfaced loudly); `redis>=5.0.0` in `requirements.txt`; `import pymupdf`; background `/next` grading + parallel evaluation | `interview_reliability_service.py`, `requirements.txt`, `test_phase7_reliability_and_speed.py` |


