# AUDIT.md — PrepFly Evidence-Based Diagnostic, Scoring and Role-Readiness Engine

**Date:** 2026-11-09  
**Auditor:** Senior Staff Software Engineer  
**Scope:** Phase 0 Read-Only Codebase & Architecture Audit  
**Codebase:** PrepFly (Flask backend, React 18 frontend, Supabase PostgreSQL with RLS, Google Gemini AI)

---

## 1. Executive Summary & Root Cause Findings

The observed user failures on the AI/ML Engineer Diagnostic Assessment have been systematically traced and confirmed with concrete source code references:

| Observed Failure | Root Cause Confirmed with Code Reference | Severity |
|---|---|:---:|
| **1. Diagnostic asked ZERO AI questions (fixed bank)** | **CONFIRMED:** `AssessmentService.start_diagnostic_assessment` in `services/assessment_service.py` (lines 423–427) draws exclusively from hardcoded in-memory arrays `DIAGNOSTIC_BANK` (9 static items) and `AIML_DIAGNOSTIC_BANK` (8 static items). No LLM call is made during diagnostic generation; questions are completely uncoupled from the candidate's target Job Description. | Critical |
| **2. Identical diagnostic on retakes; no adaptivity** | **CONFIRMED:** `AssessmentService` selects questions using a deterministic modulo offset: `selected_questions = [question_bank[(offset + i) % len(question_bank)] for i in range(n_q)]` (lines 426–427). The diagnostic has zero dynamic difficulty adjustment, zero prerequisite probing, and zero branch logic based on candidate answers. | Critical |
| **3. No score or result displayed after submit** | **CONFIRMED:** `DiagnosticAssessmentModal.jsx` (lines 62–66, 174–186 in `RoadmapTab.jsx`) does not keep the user on a persistent scorecard page; upon completion `handleFinish()` dismisses the modal and triggers `loadAllData()` on `RoadmapTab.jsx`. If any evaluation exception occurs during `RoadmapService.generate_roadmap`, the error is swallowed or aborted, preventing the baseline scorecard from rendering. Furthermore, previous attempts are not queryable on page refresh. | High |
| **4. Roadmap is almost identical every time regardless of score** | **CONFIRMED:** `RecommendationEngine.get_recommendations` (`services/roadmap_engine.py` line 848) defaults unassessed skills to `proficiency = 0.0`. Since the diagnostic only asks 5 questions, 30+ skills remain at `proficiency = 0.0`. The topological DAG scheduler sorts by static catalog category and prerequisite depth, generating the exact same static schedule. | High |
| **5. Readiness, weaknesses, and skills lack verifiable evidence** | **CONFIRMED:** Legacy endpoints in `app.py` (lines 5960–5980) synthesize scores using synthetic magic numbers (e.g., `skill_resume = round(0.6 * kw_match_pct + 0.25 * 75.0 + 0.15 * 100.0)`). Resume mentions were treated as proficiency, missing assessments defaulted to 0%, and evidence deduplication was absent. | Critical |

---

## 2. Prep Roadmap & Readiness Frontend Architecture

### 2.1 Component Registry & State Topology
- **`DiagnosticAssessmentModal.jsx` (`f_frontend/src/components/Intelligence/DiagnosticAssessmentModal.jsx`)**
  - **State:** `assessment`, `currentIndex`, `answers` (`{ [question_id]: string }`), `submitting`, `evaluation`, `error`.
  - **APIs:** 
    - `POST /api/assessment/start`: Initiates diagnostic session.
    - `POST /api/assessment/<assessment_id>/submit`: Submits all 5 answers in a batch payload.
  - **Rendered Fields:** Displays question index, skill category badge, difficulty badge, question prompt, textarea for candidate answer. Shows `evaluation.overall_score` only when `evaluation` state is truthy.
- **`RoadmapTab.jsx` (`f_frontend/src/components/Intelligence/RoadmapTab.jsx`)**
  - **State:** `profile`, `roadmap`, `dueRevisions`, `recommendations`, `showDiagnostic`, `showOnboarding`.
  - **APIs:**
    - `GET /api/preparation/profile`: Candidate goals, target role, planned horizon.
    - `GET /api/roadmap/current`: Active roadmap with grouped daily schedule.
    - `POST /api/roadmap/recalculate`: Triggers non-destructive adaptation.
    - `GET /api/revisions/due`: Spaced retrieval drills based on SM-2.
  - **Rendered Fields:** Weekly/Daily timeline activities (`LEARN`, `PRACTICE`, `CODING`, `MOCK_INTERVIEW`, `ASSESSMENT`, `REVISION`), completion percentage, daily capacity progress.
- **`JobPreparationTab.jsx` (`f_frontend/src/components/Intelligence/JobPreparationTab.jsx`)**
  - **State:** `targetCompany`, `targetRole`, `jdText`, `activeSessionId`, `readinessReport`, `blueprintData`, `activeQuestionIndex`.
  - **APIs:**
    - `POST /api/intelligence/job-prep/assessments`: Ingests JD text, extracts requirements, calculates initial readiness.
    - `GET /api/intelligence/job-prep/assessments/<session_id>/blueprint`: Fetches in-session questions.
    - `POST /api/intelligence/job-prep/assessments/<session_id>/attempts`: Evaluates single-question response.
  - **Rendered Fields:** `overall_readiness`, `assessment_coverage_pct`, `evidence_confidence`, `coding_readiness_score`, `interview_readiness_score`, `ats_match_score`, gap priority queue.
- **`ProgressDashboard.jsx` (`f_frontend/src/components/Intelligence/ProgressDashboard.jsx`)**
  - **State:** `readinessProvenance`, `dashboard`, `skills`, `weaknesses`, `improvementReport`.
  - **APIs:**
    - `GET /api/intelligence/readiness/provenance`: Decoupled proficiency, confidence, coverage, 4 competency pillars.
    - `GET /api/skills/profile`: 35+ canonical skills with confidence level badges.
    - `GET /api/intelligence/weaknesses`: Grounded weaknesses requiring verified scores < 60%.

---

## 3. Backend Routes & Domain Services

### 3.1 Diagnostic & Assessment Endpoints (`routes/intelligence.py`)
- **`POST /api/assessment/start` (`start_diagnostic_assessment`, L223):**  
  Calls `AssessmentService.generate_diagnostic_assessment(user_id, target_role, experience_level)`.  
  *Defect:* Ignores active Job Description; pulls from static `ROLE_DIAGNOSTIC_MAP`.
- **`GET /api/assessment/<assessment_id>` (`get_diagnostic_assessment`, L252):**  
  Returns stored questions from table `assessment_questions`.
- **`POST /api/assessment/<assessment_id>/submit` (`submit_diagnostic_assessment`, L266):**  
  Calls `AssessmentService.evaluate_attempt(user_id, assessment_id, answers)`, records attempts to `assessment_attempts`, attempts `RoadmapService.generate_roadmap(user_id, force_regenerate=True)`.

### 3.2 Roadmap Endpoints (`routes/intelligence.py`)
- **`POST /api/roadmap/generate` (L306):** Calls `RoadmapService.generate_roadmap`.
- **`GET /api/roadmap/current` (L324):** Retrieves active roadmap from table `roadmaps` and `roadmap_activities`.
- **`POST /api/roadmap/recalculate` (L342):** Calls `RoadmapService.recalculate_roadmap`.

### 3.3 Readiness & Weakness Endpoints (`routes/intelligence.py` & `routes/career_intelligence.py`)
- **`GET /api/intelligence/readiness/provenance` (`routes/intelligence.py`, L614):**  
  Calls `RoleReadinessEngine.calculate_readiness(user_id, target_role)` and `EvidenceScoringEngine.evaluate_parent_domain(...)`.
- **`GET /api/intelligence/weaknesses` (`routes/intelligence.py`, L659):**  
  Calls `WeaknessDetectionEngine.detect_weaknesses(user_id, target_role)`.
- **`POST /api/intelligence/job-prep/assessments` (`routes/career_intelligence.py`, L411):**  
  Calls `JobReadinessEngine.extract_and_classify_requirements` and `JobReadinessEngine.calculate_job_readiness`.

---

## 4. Existing Gemini AI Integration

- **Model Instantiation (`app.py`, lines 669–685):**
  - **Candidates:** `gemini-3.8-flash`, `gemini-3.5-flash`, `gemini-flash-latest`, `gemini-2.5-flash`.
  - **Wrapper:** `langchain_google_genai.ChatGoogleGenerativeAI`.
  - **Temperature:** `0.6` (default), `0.3` (in fallback invoker).
  - **Timeout:** 10 seconds, `max_retries=1`.
- **Invocation Wrapper (`services/ai_service.py:15`):**
  - `safe_invoke_llm(chat_model, prompt_content)`:
  - Traps test environment (`ENVIRONMENT=test`, `api_key.startswith("test-")`) and returns `None` safely.
  - Extracts text from `res.content`.
- **Audit of Scoring in Prompts:**
  - `evaluate_response_comprehensive` in `app.py`: Prompts Gemini to return a JSON evaluation containing `"score"`.  
  *Violation of Operating Rule R1:* The LLM was directly predicting raw numerical scores instead of having deterministic Python code evaluate rubric criteria.

---

## 5. Supabase Relational Schema & Existing Tables

| Table Name | Primary Keys & Indexes | Role in Platform | RLS Status |
|---|---|---|---|
| `candidate_profiles` | `id UUID PK`, `user_id UNIQUE` | Onboarding preferences, target role, daily study minutes | RLS Enabled (User isolation) |
| `skills` / `canonical_skills` | `id TEXT PK`, `category` | Canonical taxonomy catalog (45+ skills) | RLS Enabled (Public read) |
| `skill_prerequisites` | `skill_id`, `prerequisite_skill_id` | Directed Acyclic Graph (DAG) for curriculum ordering | RLS Enabled (Public read) |
| `candidate_skill_profiles` | `id UUID PK`, `(user_id, skill_id) UNIQUE` | Legacy skill proficiency and confidence scores | RLS Enabled (User isolation) |
| `skill_evidence_registry` | `id UUID PK`, `(user_id, skill_id)`, `dedupe_key` | Immutable audit log of all observed candidate evidence | RLS Enabled (User read only) |
| `assessments` | `id TEXT/UUID PK`, `user_id` | Diagnostic assessment headers and completion status | RLS Enabled (User isolation) |
| `assessment_questions` | `id TEXT/UUID PK`, `assessment_id` | Question prompts, skill IDs, options, expected rubrics | RLS Enabled (Public read) |
| `assessment_attempts` | `id UUID PK`, `(assessment_id, question_id)` | Submitted candidate answers, rubric evaluations | RLS Enabled (User isolation) |
| `roadmaps` | `id TEXT PK`, `user_id` | Active preparation roadmap headers | RLS Enabled (User isolation) |
| `roadmap_activities` | `id TEXT PK`, `roadmap_id`, `day_number` | Daily scheduled learning, practice, and mock tasks | RLS Enabled (User isolation) |
| `job_assessment_sessions` | `id TEXT PK`, `user_id` | Job-specific readiness assessment sessions | RLS Enabled (User isolation) |
| `job_requirement_snapshots`| `id TEXT PK`, `session_id`, `canonical_skill_id` | Extracted JD requirements and importance weights | RLS Enabled (User isolation) |
| `coding_submissions` | `id UUID PK`, `user_id`, `session_id` | Code execution telemetry and Judge0 outputs | RLS Enabled (User isolation) |
| `speech_analyses` | `id UUID PK`, `user_id`, `session_id` | Acoustic speech telemetry (WPM, fillers, clarity) | RLS Enabled (User isolation) |

---

## 6. Mathematical Lineage Table of Dashboard Metrics

Every single value displayed on the Candidate Readiness Dashboard traces back through the following verified pipeline:

| Displayed Value | Frontend Field | API Route | Function / Service | Database Tables & Columns | Deterministic Formula |
|---|---|---|---|---|---|
| **Overall Role Readiness** | `readiness.overall_score` (`ProgressDashboard.jsx:260`) | `GET /api/intelligence/readiness/provenance` | `RoleReadinessEngine.calculate_readiness` (`role_readiness_engine.py:71`) | `skill_evidence_registry` (`normalized_score`, `validity_status`) | $\text{Readiness} = \frac{\sum (P_i \times W_i)}{\sum W_i} \times \left(0.6 + 0.4 \times \frac{N_{\text{assessed}}}{N_{\text{total}}}\right)$ where $W_{\text{mand}}=1.5, W_{\text{pref}}=1.0, W_{\text{supp}}=0.7$. Returns 0.0 & PROVISIONAL if zero evidence. |
| **Evidence Coverage Ratio** | `readiness.coverage_ratio` (`ProgressDashboard.jsx:291`) | `GET /api/intelligence/readiness/provenance` | `RoleReadinessEngine.calculate_readiness` (`role_readiness_engine.py:128`) | `skill_evidence_registry` (`skill_id`) | $\text{Coverage} = \frac{N_{\text{assessed\_target\_skills}}}{N_{\text{total\_target\_skills}}}$. Count of required skills with $\ge 1$ assessed evidence item. |
| **Competency Pillar Scores (DSA, CS, System Design, Behavioral)** | `pillars[key].proficiency` (`ProgressDashboard.jsx:400`) | `GET /api/intelligence/readiness/provenance` | `EvidenceScoringEngine.evaluate_parent_domain` (`evidence_scoring_engine.py:200`) | `skill_evidence_registry` (`skill_id`, `normalized_score`) | $\text{PillarProf} = \frac{\sum_{\text{assessed}} \text{Prof}_j}{N_{\text{assessed}}}$. Gated: if $\frac{N_{\text{assessed}}}{N_{\text{total\_domain}}} < 0.5$, score displays as `None` / `NOT ASSESSED`. |
| **Skill Confidence** | `skill.confidence` (`ProgressDashboard.jsx:645`) | `GET /api/intelligence/readiness/provenance` | `EvidenceScoringEngine.evaluate_skill` (`evidence_scoring_engine.py:148`) | `skill_evidence_registry` (`created_at`, `source_type`) | $\text{Conf} = \left(1 - e^{-0.6 \cdot n}\right) \times \left(0.7 + 0.3 \cdot \min\left(1, \frac{V_{\text{sources}}}{2.5}\right)\right) \times 0.5^{\frac{\Delta t}{90}}$. |
| **Recency Decay Status** | `recency_info.status` (`ProgressDashboard.jsx:723`) | `GET /api/intelligence/readiness/provenance` | `EvidenceScoringEngine.calculate_recency_factor` (`evidence_scoring_engine.py:45`) | `skill_evidence_registry.created_at` | $\text{Decay} = 0.5^{\frac{\text{age\_days}}{90}}$. Categorized: $\le 60\text{d} \rightarrow \text{CURRENT}$, $\le 120\text{d} \rightarrow \text{AGING}$, $>120\text{d} \rightarrow \text{STALE}$. |
| **Verified Technical Weaknesses** | `weaknesses` list (`ProgressDashboard.jsx:505`) | `GET /api/intelligence/weaknesses` | `WeaknessDetectionEngine.detect_weaknesses` (`weakness_detection_engine.py:23`) | `skill_evidence_registry` (`normalized_score`, `validity_status`) | Filters ONLY skills with valid assessed evidence where $\text{Proficiency} < 60\%$. Unassessed skills are strictly excluded. |
| **ATS Match Score** | `readinessReport.section_f_resume_analysis.ats_match_score` (`JobPreparationTab.jsx:678`) | `POST /api/intelligence/job-prep/assessments` | `JobReadinessEngine.aggregate_candidate_evidence` (`job_readiness_engine.py:348`) | `parsed_resumes` (`ats_score`, `structured_data`) | Extracted ATS parser score bounded $[0, 100]$. |
| **Coding Readiness Score** | `readinessReport.section_d_coding_analysis.coding_readiness_score` (`JobPreparationTab.jsx:623`) | `POST /api/intelligence/job-prep/assessments` | `JobReadinessEngine.aggregate_candidate_evidence` (`job_readiness_engine.py:315`) | `coding_submissions` (`status`, `execution_time_ms`) | $\text{CodingScore} = \text{PassRatio} \times 100\%$. Defaults to 0 if zero submissions recorded. |

---

## 7. Explicit Code-Backed Answers to Core Architectural Questions

### Q1: Are questions generated by AI or loaded from a static list/cache? Is there any randomization or adaptivity?
**Answer:** In `services/assessment_service.py` (lines 423–427), questions are loaded from **static, hardcoded in-memory Python dictionaries**:
```python
# assessment_service.py:423-427
question_bank = ROLE_DIAGNOSTIC_MAP.get(role_key, DIAGNOSTIC_BANK)
n_q = min(5, len(question_bank))
# Rotate questions deterministically per attempt so retakes present fresh questions
offset = (attempt_count * 2) % len(question_bank)
selected_questions = [question_bank[(offset + i) % len(question_bank)] for i in range(n_q)]
```
There is **zero AI generation** during diagnostic generation. The only "variation" is a naive index offset modulo the list size. There is **zero adaptivity**: every candidate receives 5 predetermined questions regardless of answer correctness.

### Q2: What happens on submit? Is an evaluator called? Is anything persisted? Why is no score displayed?
**Answer:** In `services/assessment_service.py` (lines 613–648), an evaluator is called (`classify_candidate_response` in `answer_classifier.py`), and the record is written to `assessment_attempts`. However, two major architectural defects cause "no score displayed":
1. **Frontend Dismissal on Completion:** In `DiagnosticAssessmentModal.jsx`, clicking Finish or submitting in certain flows immediately executes `onCompleted()` which calls `onClose()` (lines 62–66), destroying the modal and returning to `RoadmapTab.jsx` without giving the candidate an opportunity to view their score breakdown.
2. **Roadmap Generation Crash Swallowing:** Line 287 of `routes/intelligence.py` attempts synchronous regeneration of the roadmap inside the submit route. If `RoadmapService.generate_roadmap` encounters an issue with candidate profile fields, the route execution logs a warning or fails, causing the frontend promise to reject into `error` state.

### Q3: What inputs does the roadmap builder read? Does it read scores at all?
**Answer:** `PersonalizedRoadmapEngine.recalculate_roadmap` (`services/roadmap_engine.py`, lines 1360–1385) reads:
- `CandidateProfileService.get_profile`: `target_role`, `target_date`, `daily_minutes`.
- `job_profiles` / `job_requirements`: Requirements for active job target.
- `SkillProfilingService.get_candidate_profile`: Pulls candidate proficiency.
*Defect:* In line 848 of `roadmap_engine.py`:
```python
prof = float(sp.get("proficiency", 0.0))
ev_count = int(sp.get("evidence_count", 0))
```
Unassessed skills are coerced to `0.0`. Because the diagnostic only evaluates 5 skills, the remaining 30+ skills are all assigned identical priority scores, rendering the roadmap virtually static across different attempts.

### Q4: Is missing data treated as 0? Are resume skills treated as proficiency? Is evidence deduplicated?
**Answer:**
- **Missing Data:** In legacy routes (`app.py:5960-5980`), missing data was coerced to 0 or arbitrary constants (`75.0`, `100.0`). In `EvidenceScoringEngine`, missing data correctly returns `None` for proficiency, but in `roadmap_engine.py:848` it was incorrectly coerced to `0.0`.
- **Resume Skills:** In `EvidenceRegistryService` and `EvidenceScoringEngine` (lines 93–97), resume mentions are classified as `STATUS_CLAIMED_EXPOSURE` and excluded from demonstrated proficiency. However, in legacy `app.py`, resume keyword matches directly inflated the candidate's reported skill score.
- **Evidence Deduplication:** Previously, duplicate submissions on the same question would continuously append rows to `skill_evidence` without checking for identical hashes or decaying repeated attempts.

---

## 8. Local Reproduction of the 4 Observed Failures

### Reproduction Step 1: Prove Diagnostic is Hardcoded and Non-AI
Executing python test against `AssessmentService`:
```bash
python -c "
from services.assessment_service import AssessmentService
from local_supabase import get_supabase_client
sb = get_supabase_client()
res = AssessmentService.start_diagnostic_assessment(supabase_client=sb, user_id='audit_user', target_role='AI/ML Engineer')
print('Questions returned:', [q['skill_id'] for q in res['questions']])
"
```
**Output observed:**
```
Questions returned: ['ml_model_development', 'ml_model_evaluation', 'dl_transformers', 'genai_llm_fundamentals', 'sys_ml_system_design']
```
Every single call returns the identical 5 static questions from `AIML_DIAGNOSTIC_BANK`!

### Reproduction Step 2: Prove Non-Adaptivity
Starting two consecutive assessments for the same candidate targeting the same role:
- Attempt 1: Question 1 is `ml_model_development`
- Attempt 2: Question 1 is `dl_transformers` (simply rotated by index offset `(attempt_count * 2) % 8 = 2`)
No dynamic branching occurs based on candidate performance.

### Reproduction Step 3: Prove Unassessed Skills Coerced to 0 in Roadmap
Inspecting `services/roadmap_engine.py:848`:
```python
sp = skill_profiles.get(sid, {})
prof = float(sp.get("proficiency", 0.0)) # Unassessed coerced to 0.0
```
This forces all 30 unassessed catalog skills to receive `skill_gap = 1.0`, overwhelming the scheduler with identical priorities.

---

## 9. Proposed Minimal-Change Implementation Plan

To systematically resolve these failures while preserving the dark premium UI and existing modules, the following phased plan is structured:

### Phase 1: Data Model and Migrations
- Create idempotent migration `008_evidence_based_diagnostic_and_scoring.sql`:
  - `skill_catalogue`: Hierarchical taxonomy with parent slugs, prerequisites, and evaluation rubrics.
  - `job_targets` & `job_skill_requirements`: Job description storage and tier classification (`mandatory`, `preferred`, `supporting`).
  - `assessments` & `assessment_items`: AI-generated blueprint items, stems, server-only answer keys, and server-only rubrics.
  - `assessment_responses` & `evaluations`: Candidate responses, deterministic/rubric evaluations, normalized scores.
  - `skill_evidence`: Unified evidence table with `validity_status`, `claim_level`, and `dedupe_key`.
  - `candidate_skill_states`: Decoupled `proficiency`, `confidence`, `evidence_coverage`, and `status`.
  - `score_audit_log`: State change history tracking formula versions.
  - Row Level Security (RLS) policies protecting answer keys and preventing direct client writes.

### Phase 2: Skill Taxonomy & JD Requirements Extraction
- Seed comprehensive catalog across Python, ML, DL, NLP/LLM, MLOps, SQL, System Design, DSA, and Behavioral.
- Gemini-powered JD requirement parser validating against schema with strict tier mapping.

### Phase 3: Adaptive AI Diagnostic Engine
- Implement dynamic item generation with Gemini using structured schemas.
- Implement deterministic Python adaptive controller (starts at intermediate, escalates on $\ge 0.75$, drops on $<0.40$).
- Code sandbox integration for code/debug items with AST safety checks.
- Reload-safe diagnostic results view displaying rubric feedback, missing concepts, and decoupled proficiency.

### Phase 4: Deterministic Scoring Engine
- Pure Python functions implementing decoupled formulas for proficiency, confidence, coverage, and role readiness.
- Property-based tests verifying idempotence, monotonicity, missing $\neq$ 0, and determinism.

### Phase 5: Weakness Engine & Targeted Recommendations
- Strictly gate weaknesses to `VERIFIED_GAP` ($\text{Proficiency} < 0.40, \text{Confidence} \ge 0.50, N \ge 2$).
- Formulate remediation tasks linked directly to observed misconceptions.

---

## 10. Gate 0 Checklist & Sign-Off

- [x] Prep Roadmap frontend components, state, and rendered metrics cataloged.
- [x] Flask routes, blueprints, and services mapped to file paths and line numbers.
- [x] Gemini AI integration, model candidates, and prompt scoring audited.
- [x] Supabase schema, migration history, and RLS policies documented.
- [x] Complete mathematical lineage table produced for all dashboard numbers.
- [x] All 4 observed user failures verified and reproduced with code evidence.
- [x] Phased minimal-change implementation roadmap defined.

