# ARCHITECTURE & ENGINEERING DECISION RECORDS (ADRs) — PREPFLY

**Document Version:** 2.0.0  
**Status:** Approved Architectural Baseline  
**Scope:** Core System Decisions, Persistence Invariants, AI Orchestration & Scalability Trade-offs  

---

## ADR-001: Modular Monolith vs Distributed Microservices
- **Status:** **ACCEPTED**
- **Context:**  
  PrepFly coordinates real-time multi-modal telemetry (speech acoustics, code sandbox execution, LLM question synthesis, and relational curriculum planning). An early architectural proposal suggested breaking the backend into separate microservices (Auth Service, Interview Service, Diagnostic Service, Billing Service, Telemetry Service).
- **Decision:**  
  Retain a **Modular Monolith** built on Python Flask (`app.py`), domain-separated Flask Blueprints (`routes/`), and 38 in-process domain services (`services/`).
- **Consequences & Trade-offs:**
  - *Positive:* Zero network hop latency and serialization overhead between internal modules. Atomic cross-domain transactions. Greatly simplified CI/CD deployment pipelines on Render with a single build container.
  - *Negative:* All modules share memory within the same operating process; heavy CPU tasks (e.g. PDF parsing) must be managed carefully to prevent event-loop starvation.

---

## ADR-002: Dual Persistence Strategy (Supabase PostgreSQL with SQLite Fallback)
- **Status:** **ACCEPTED**
- **Context:**  
  Cloud-hosted database instances (Supabase PostgreSQL via PostgREST) occasionally suffer from transient network partitions, DNS resolution failures, or connection pool exhaustion during traffic surges. If the backend fails closed on every transient network drop, candidates taking live 15-minute interviews lose their in-flight transcripts.
- **Decision:**  
  Implement a transparent dual-persistence proxy in `local_supabase.py` (`SQLiteSupabaseMock` and `RealBuilderWrapper`). When the remote Supabase client experiences DNS or socket failure, it transparently falls back to a local file-backed SQLite database (`/tmp/prepfly_local.sqlite` on Linux, local directory on Windows) with identical builder semantics.
- **Consequences & Trade-offs:**
  - *Positive:* Zero user-facing interview drops during cloud maintenance or network blips.
  - *Negative:* State saved to local SQLite must be reconciled with Supabase upon reconnection; SQLite is process-local unless backed by shared persistent disks.

---

## ADR-003: Deterministic Python Scoring vs Direct LLM Score Output
- **Status:** **ACCEPTED**
- **Context:**  
  Generative AI models (e.g. Gemini, GPT-4) can easily hallucinate numerical scores or exhibit high variance across identical answers depending on slight temperature shifts.
- **Decision:**  
  The LLM is strictly restricted to qualitative evaluation: extracting demonstrated concepts, identifying misconceptions, and generating verbal justifications against rubrics. **All mathematical aggregation, proficiency scoring, confidence saturation, recency decay, and readiness weighting are computed by deterministic Python code** in `evidence_scoring_engine.py` and `role_readiness_engine.py`.
- **Consequences & Trade-offs:**
  - *Positive:* 100% reproducible, auditable scores that can be mathematically defended before candidates and university placement directors. Fully testable via property-based unit tests.
  - *Negative:* Requires engineering and maintaining comprehensive rubric taxonomies and concept-matching rules in Python.

---

## ADR-004: Live Turn Telemetry Assembly vs Post-Interview Batch Scoring
- **Status:** **ACCEPTED**
- **Context:**  
  Traditional mock interview platforms collect all turns and send a massive transcript to an LLM when the user clicks "End Interview", causing a 15–30 second loading spinner while the candidate waits for results.
- **Decision:**  
  Evaluate each turn in parallel during the interview (`POST /next`). When `POST /end-interview` is invoked, `fast_compile_report` compiles the accumulated turn evaluations into a comprehensive scorecard in under **1 millisecond**.
- **Consequences & Trade-offs:**
  - *Positive:* Instantaneous scorecard display at session conclusion; zero candidate drop-off during report generation.
  - *Negative:* Increases per-turn latency during `/next` by ~600ms, which is mitigated by running next-question generation and response evaluation concurrently via `ThreadPoolExecutor(max_workers=2)`.

---

## ADR-005: Tiered Caching (L1 In-Memory LRU + L2 Upstash Redis)
- **Status:** **ACCEPTED**
- **Context:**  
  Repeated queries for the canonical skill taxonomy (45+ skills), role requirement weights, and static assessment rubrics consume unnecessary database bandwidth.
- **Decision:**  
  Implement a tiered caching strategy: sub-millisecond L1 in-memory dictionary cache with TTL invalidation, backed by a distributed Upstash Redis L2 cache with SHA-256 content-addressed keys. If Redis is unreachable, the system gracefully falls back to L1 Memory without throwing 500 errors.
- **Consequences & Trade-offs:**
  - *Positive:* Database query volume reduced by $>70\%$ on hot read paths.
  - *Negative:* Distributed cache invalidation requires explicit event triggers on data mutation.

---

## ADR-006: Abstract Syntax Tree (AST) Sandboxed Code Execution
- **Status:** **ACCEPTED**
- **Context:**  
  Candidate coding submissions in `CodingTab.jsx` require execution against test cases. Using an external Judge0 cluster introduces network costs, latency, and operational dependencies. Running user code directly on the host enables remote code execution (RCE).
- **Decision:**  
  Implement an in-engine AST sandbox (`code_sandbox_service.py`): code is parsed into Python AST nodes, verified against a strict whitelist of permitted language constructs, stripped of all system/network/file built-ins, and executed inside an ephemeral subprocess with a 5.0-second timeout and 128MB memory ceiling.
- **Consequences & Trade-offs:**
  - *Positive:* Completely secure, local, sub-50ms code grading with zero external API dependencies.
  - *Negative:* Highly specialized or multi-file projects require external container runners.

