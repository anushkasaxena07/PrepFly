# TECHNICAL DEBT REGISTRY & REMEDIATION ROADMAP — PREPFLY

**Document Version:** 2.0.0  
**Classification:** Senior Staff Engineering Technical Debt Assessment  
**Audit Scope:** Codebase Maintainability, Refactoring Priorities & Architectural Hardening  

---

## 1. Technical Debt Inventory & Impact Matrix

| # | Technical Debt Item | Location | Complexity / Effort | Risk Level | Architectural Impact |
|---|---|---|:---:|:---:|---|
| **TD-1** | **Monolithic Gateway Size (`app.py`)** | `f_backend/app.py` (~11,154 LOC) | **High** (32 hrs) | **Medium** | `app.py` contains legacy route handlers that should be decomposed into dedicated Blueprints (`routes/auth.py`, `routes/billing.py`, `routes/analytics.py`). |
| **TD-2** | **Hardcoded Diagnostic Banks in Assessment Service** | `f_backend/services/assessment_service.py:22-232` | **Medium** (16 hrs) | **High** | `DIAGNOSTIC_BANK` (9 items) and `AIML_DIAGNOSTIC_BANK` (8 items) are static Python dictionaries instead of dynamically synthesized Gemini items conditioned on JD requirements. |
| **TD-3** | **Legacy Analytics Magic Numbers** | `f_backend/app.py:5960-5980` | **Low** (8 hrs) | **High** | Legacy route `/analytics/stats` calculates resume skill scores using arbitrary magic formulas (`round(0.6 * kw_match_pct + 0.25 * 75.0 + 0.15 * 100.0)`). Should consume `EvidenceScoringEngine` exclusively. |
| **TD-4** | **Frontend Cockpit Component Weight (`AvaTab.jsx`)** | `f_frontend/src/components/AvaTab.jsx` (~2,640 LOC) | **Medium** (20 hrs) | **Low** | `AvaTab.jsx` mixes WebRTC audio recording, VAD state, video preview, turn rendering, and final report generation in a single monolithic React component. |
| **TD-5** | **PostgREST Schema Cache Invalidation Lag** | Supabase PostgREST Gateway | **Low** (4 hrs) | **Medium** | Migrations adding new columns require explicit `NOTIFY pgrst, 'reload schema';` calls to avoid `PGRST204` column mismatch errors. |
| **TD-6** | **Unassessed Skills Coerced to 0.0 in Roadmap Engine** | `f_backend/services/roadmap_engine.py:848` | **Low** (6 hrs) | **Medium** | `prof = float(sp.get("proficiency", 0.0))` forces unassessed skills to `skill_gap = 1.0`, leading to repetitive roadmap schedules across retakes. |

---

## 2. In-Depth Debt Analyses & Solutions

### TD-1: Monolithic Gateway Decomposition (`app.py`)
- **Current State:**  
  `app.py` is ~11,154 lines long. While 4 clean Blueprints (`intelligence.py`, `career_intelligence.py`, `interview.py`, `mentor.py`) have already been extracted, `app.py` still contains authentication routes, Razorpay payment handlers, and legacy analytics endpoints.
- **Remediation Plan:**
  1. Extract `routes/auth_routes.py` (OTP login, Google verify, profile updates).
  2. Extract `routes/billing_routes.py` (Razorpay orders, webhooks, invoice downloads).
  3. Extract `routes/support_routes.py` (Ticket creation, candidate feedback, superadmin triage).
  4. Shrink `app.py` to $< 1,000$ lines acting purely as the Flask application factory.

---

### TD-2: Transitioning Static Question Banks to Adaptive AI Synthesis
- **Current State:**  
  `assessment_service.py` defines `DIAGNOSTIC_BANK` and `AIML_DIAGNOSTIC_BANK` directly in code. retakes merely rotate through the bank using modulo indexing (`(offset + i) % len(bank)`).
- **Remediation Plan:**
  1. Replace static banks with dynamic item generation via Gemini using strict JSON schemas (Phase 3 of Prompt 1).
  2. Implement the deterministic adaptive controller: strong answer ($\ge 0.75$) $\rightarrow$ increase difficulty; weak answer ($< 0.40$) $\rightarrow$ decrease difficulty and queue prerequisite probe.
  3. Ensure variation guarantee: hash exclusion list prevents candidates from ever seeing the same stem hash across retakes.

---

### TD-3: Unified Migration of Legacy Analytics to Evidence Engine
- **Current State:**  
  The endpoint `GET /analytics/stats` in `app.py` (lines 5960–5980) contains legacy code that calculates resume and DSA scores using hardcoded heuristic formulas:
  ```python
  skill_resume = round(0.6 * kw_match_pct + 0.25 * 75.0 + 0.15 * 100.0)
  ```
- **Remediation Plan:**
  Replace legacy heuristics with direct calls to `RoleReadinessEngine.calculate_readiness` and `EvidenceScoringEngine.evaluate_skill`, ensuring all displayed dashboard values originate from verifiable, recorded evidence rows.

---

### TD-4: Component Decomposition of `AvaTab.jsx`
- **Current State:**  
  `AvaTab.jsx` contains 2,640 lines of React code managing MediaStream audio permissions, speech-to-text base64 encoding, live turn captions, in-interview question rendering, and scorecard display.
- **Remediation Plan:**
  Decompose into smaller, single-responsibility components:
  - `src/components/Interview/AudioTelemetryController.jsx` (MediaRecorder and VAD).
  - `src/components/Interview/InterviewTurnViewer.jsx` (Question prompt and candidate transcript).
  - `src/components/Interview/InterviewScorecardModal.jsx` (Final report display).

