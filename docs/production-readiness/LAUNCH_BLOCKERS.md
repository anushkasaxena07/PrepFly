# 🛑 PrepFly Prioritized Launch Blockers & Action Plan (`LAUNCH_BLOCKERS.md`)

This document defines the prioritized remediation backlog required before PrepFly can transition from its current engineering prototype status to commercial launch.

---

## 🚦 Priority Definitions
* **P0 — Critical Blocker**: Must be resolved before accepting any real customers or payments. Security flaws, data isolation failures, broken core customer journeys, or severe legal/financial liabilities.
* **P1 — High Priority**: Must be resolved prior to public release. Broken administrative flows, unmonitored AI token spending, missing production manifests.
* **P2 — Medium Priority**: Usability enhancements, automated DB backups, load testing, and operational runbook dry runs.
* **P3 — Low Priority**: Non-blocking improvements, minor UI polish, documentation refinements.

---

## 📊 Launch Blockers Master Tracking Table

| Blocker ID | Priority | Category | Description | Owner | Acceptance Criteria | Status |
| :--- | :---: | :---: | :--- | :--- | :--- | :---: |
| **BLOCKER-01** | **P0** | Frontend | Hardcoded `http://localhost:5000` URLs in PaymentHistory & InvoiceTable. | Frontend Lead | 0 occurrences of `localhost:5000` in `f_frontend/src`. Invoices download via dynamic `BACKEND_URL` and Bearer token. | **RESOLVED** *(Verified in Code & Tests)* |
| **BLOCKER-02** | **P0** | Security / SRE | `ISOLATED_SANDBOX_URL` missing from staging and production configuration. | SRE / DevOps | `ISOLATED_SANDBOX_URL` and `ISOLATED_SANDBOX_SECRET` set in staging & production environments. Fail-closed preserved. | **OPEN** *(Deployment Runbook Authored; Staging VPS Provisioning Pending Approval)* |
| **BLOCKER-03** | **P0** | Frontend | Inconsistent fallback URLs across 12+ API service files. | Frontend Lead | Centralized `BACKEND_URL` imported from `@/config/api` across all service modules. | **RESOLVED** *(Verified in Code)* |
| **BLOCKER-04** | **P0** | Legal / Compliance | DPDP Act 2023 consent checkbox & privacy policy missing on signup. | Legal / Frontend | Explicit consent checkbox recorded in DB; Privacy Policy and Refund terms published. | **OPEN** |
| **BLOCKER-05** | **P0** | Commercial | Hardcoded ₹500/year pricing model creates severe unit economics deficit. | Product / Backend | Multi-tier plan pricing parameterized and validated on the server. | **OPEN** |
| **BLOCKER-06** | **P0** | Security / Auth | Client-supplied `user_id` parameter spoofing across session and feedback endpoints. | Security Lead | All endpoints bind strictly to JWT `sub`. Client-supplied user IDs rejected with HTTP 403. | **RESOLVED** *(Verified in 52 Data Isolation Tests)* |
| **BLOCKER-07** | **P0** | Security / SRE | Sandbox runtime isolation (cgroups, non-root UID 10001, `--network none`) unverified on Linux host. | SRE / Security | Execute all 8 Linux staging isolation gates on provisioned Linux host with documented evidence. | **NOT TESTED** *(Code Hardened; Live Linux Staging Execution Pending)* |

---

## 🚨 P0 — Critical Blockers (Detail & Verification)

### BLOCKER-01: Hardcoded Localhost URLs in Remote Frontend Components
* **Issue**: Multiple React components contained hardcoded `http://localhost:5000` URLs instead of using the dynamic environment backend URL.
* **Severity**: **P0 (Critical)**
* **Owner**: Frontend Lead
* **Evidence**:
  - `f_frontend/src/components/Admin/PaymentHistory.jsx`: Previously used `window.open("http://localhost:5000/api/invoice/${invoiceId}", "_blank");`.
  - `f_frontend/src/components/Admin/InvoiceTable.jsx`: Previously used `href={"http://localhost:5000/api/invoice/${inv.id}"}`.
* **Resolution**:
  Replaced direct query string URLs with authenticated `downloadInvoice()` helper utilizing dynamic `BACKEND_URL` and `Authorization: Bearer <token>` headers with blob downloads.
* **Acceptance Criteria**: All invoice PDF download buttons resolve to the correct domain when accessed on staging or production.
* **Status**: **RESOLVED**

---

### BLOCKER-02: `ISOLATED_SANDBOX_URL` Missing from Configuration
* **Issue**: The code execution route `/api/coding/submit` strictly aborts with HTTP 503 if `ISOLATED_SANDBOX_URL` is missing. The variable is omitted from `.env`.
* **Severity**: **P0 (Critical)**
* **Owner**: SRE / DevOps
* **Evidence**:
  - [`f_backend/app.py:L2781`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2781):
    ```python
    if not os.getenv("ISOLATED_SANDBOX_URL"):
        return jsonify({"error": "Service Unavailable: Code execution requires an isolated sandbox worker"}), 503
    ```
  - [`f_backend/.env`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/.env): No `ISOLATED_SANDBOX_URL` defined.
* **Business Impact**: Paying students attempting coding assessments in production will be unable to run or submit code, rendering the coding module completely non-functional.
* **Required Fix**:
  1. Provision dedicated small Linux staging VPS and deploy worker daemon with Caddy reverse proxy (`sandbox.staging.prepfly.io`).
  2. Set `ISOLATED_SANDBOX_URL=https://sandbox.staging.prepfly.io` and `ISOLATED_SANDBOX_SECRET` in staging backend environment.
* **Acceptance Criteria**:
  1. `ISOLATED_SANDBOX_URL` is configured in staging and production to a valid HTTPS endpoint.
  2. `ISOLATED_SANDBOX_SECRET` is generated with 256-bit entropy (`openssl rand -hex 32`) and matches on backend and worker.
  3. `POST /api/coding/submit` succeeds and executes test cases when the worker is online.
  4. Fail-closed verified: when `ISOLATED_SANDBOX_URL` is unset or worker is unreachable, backend returns **HTTP 503** with zero host code execution.
* **Status**: **OPEN** *(Deployment Runbook Authored in PREPFLY_LINUX_STAGING_DEPLOYMENT_PLAN.md; Provisioning Pending User Approval)*

---

### BLOCKER-03: Inconsistent API Fallbacks across Frontend Service Modules
* **Issue**: 12+ frontend service files used `import.meta.env.VITE_BACKEND_URL || "http://localhost:5000"` while core pages used dynamic hostname detection.
* **Severity**: **P0 (Critical)**
* **Owner**: Frontend Lead
* **Resolution**: Updated frontend API callers to use centralized backend resolution logic.
* **Acceptance Criteria**: All frontend modules import `BACKEND_URL` dynamically.
* **Status**: **RESOLVED**

---

### BLOCKER-04: DPDP Act 2023 & Privacy / Terms Legal Non-Compliance
* **Issue**: PrepFly captures candidate voices, resumes with personal identifiable information (PII), and evaluation metrics without published Terms of Service, Privacy Policy, or explicit consent notices.
* **Severity**: **P0 (Critical / Legal)**
* **Owner**: Legal / Frontend Lead
* **Evidence**: No Privacy Policy or Terms of Service links exist on the login or onboarding screens. Resumes are sent across borders to Google Gemini servers without user notification.
* **Business Impact**: Potential penalties under the Digital Personal Data Protection Act (DPDP Act 2023) in India (up to ₹250 crore for significant data fiduciary violations) and violation of consumer protection disclosure requirements.
* **Required Fix**:
  1. Draft and publish a comprehensive Privacy Policy and Terms of Service.
  2. Implement an explicit checkbox on candidate signup: *"I consent to the processing of my resume and interview responses for placement evaluation."*
  3. Include a clear Refund & Cancellation Policy for subscription purchases.
* **Acceptance Criteria**: Links are visible on all registration and checkout pages with recorded consent timestamps.
* **Status**: **OPEN**

---

### BLOCKER-05: Hardcoded ₹500/Year Pricing Model Creates Unviable Unit Economics
* **Issue**: Backend `payment_service.py` hardcodes ₹500 INR (~$6 USD) per year for an entire college organization, while API calls to Google Gemini have no usage caps.
* **Severity**: **P0 (Commercial)**
* **Owner**: Product Lead / Backend Lead
* **Evidence**:
  - [`f_backend/services/payment_service.py:L90`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/services/payment_service.py#L90): `"amount": 500.0`
  - A college of 300 students running 10 mock interviews each costs ~₹3,750 in raw Gemini API tokens against ₹500 in collected revenue (750% loss).
* **Business Impact**: Immediate commercial bankruptcy as customer adoption scales.
* **Required Fix**:
  1. Parameterize plan pricing: Student Pro (₹499/mo), College Tier (₹25,000/yr for up to 200 students).
  2. Store plan entitlements in the database and pass the verified amount to Razorpay.
* **Acceptance Criteria**: Razorpay orders are generated with plan-specific amounts validated on the server.
* **Status**: **OPEN**

---

### BLOCKER-06: Client-Supplied `user_id` Session Spoofing
* **Issue**: Route `/upload` and `/create-session-no-resume` previously accepted arbitrary `user_id` parameters from request bodies.
* **Severity**: **P0 (Security)**
* **Owner**: Security Lead
* **Resolution**:
  Enforced `user_id = request.current_user["sub"]` from decoded JWT across all session, upload, feedback, and submission routes. Client-provided user IDs are strictly rejected with HTTP 403 unless caller is ADMIN or SUPER_ADMIN.
* **Acceptance Criteria**: All session creation and mutation routes bind strictly to the caller's JWT token. Verified in 52 data isolation automated test cases.
* **Status**: **RESOLVED**

---

### BLOCKER-07: Sandbox Runtime Container Isolation Unverified on Linux Host
* **Issue**: Development host is Windows without Docker/WSL. While code-level unit tests and fail-closed checks pass, runtime kernel enforcement (UID 10001, cgroups memory/CPU/PID capping, `--network none` outbound blocking, and ro-rootfs) has not been verified on a Linux kernel.
* **Severity**: **P0 (Security / SRE)**
* **Owner**: SRE / Security Lead
* **Acceptance Criteria**:
  Execute all 8 audited verification gates on a live Linux staging host (Ubuntu 22.04 LTS cgroups v2) and capture terminal evidence:
  1. Non-root execution confirmed (UID/GID 10001) via both direct Docker and `/execute` HTTP API.
  2. Memory limit cgroups v2 kill confirmed (Exit code 137 / `oom-kill:constraint=CONSTRAINT_MEMCG`) with swap containment (`--memory-swap=128m`).
  3. CPU throttling confirmed via CFS quota and wall-clock execution hard timeout confirmed at 4.0s (`status: time_limit_exceeded`).
  4. Fork-bomb bounded PID limit confirmed via cgroups v2 (`BlockingIOError`) with zero impact on host PID table.
  5. Complete outbound network and DNS isolation confirmed (`--network none`, socket/curl failures: `Network is unreachable`).
  6. Cloud metadata (`169.254.169.254`) blocked and host secrets confirmed scrubbed from execution environment.
  7. Read-only filesystem confirmed (`[Errno 30] Read-only file system`) and ephemeral scratch directories confirmed purged (`ORPHANED_TEMP_DIRS=0`).
  8. Fail-closed chaos test confirmed: stopping the worker service returns **HTTP 503** with 0 host execution.
  *Note on Privilege Model:* Staging utilizes standard Docker on a dedicated, isolated VPS (zero production secrets/databases). Production requires gVisor (`runsc`) or Rootless Docker to eliminate host daemon privilege risks.
* **Status**: **NOT TESTED** *(Code Hardening & Unit Tests Complete; Live Linux Staging Gates Pending Infrastructure Approval)*

---

## ⚠️ P1 — High Priority (Pre-Launch Requirements)

| Finding ID | Issue Description | Affected Component | Required Action | Status |
| :--- | :--- | :--- | :--- | :---: |
| **P1-01** | Missing Per-User AI Token Quotas | `f_backend/app.py` | Add daily limit of 5 AI interviews per student per day to prevent quota exhaustion. | OPEN |
| **P1-02** | Live Razorpay Webhook Verification | `services/webhook_service.py` | Configure and test live production webhook secret with Razorpay merchant account. | OPEN |
| **P1-03** | Production Database Automated Backup | Supabase Managed | Verify that automated daily point-in-time recovery (PITR) backups are enabled. | OPEN |
| **P1-04** | Monolithic `app.py` Architecture | `f_backend/app.py` | Split 9,700-line `app.py` into modular Flask Blueprints (`routes/auth.py`, `routes/interview.py`). | OPEN |
| **P1-05** | Production Mode Enforcement | `f_backend/.env` | Ensure `FLASK_ENV=production` is set in production deployment to disable SQLite fallback. | OPEN |
| **P1-06** | Sentry Alerting & PagerDuty Rules | Sentry Dashboard | Configure email alerts for 5xx error rate spikes > 1% over 5 minutes. | OPEN |
| **P1-07** | E2E Browser Testing in CI/CD | `.github/workflows/ci.yml` | Add headless Playwright workflow testing student onboarding and coding flow. | OPEN |
| **P1-08** | Multi-Tier Cache Eviction on Org Change | `services/cache_service.py` | Invalidate `sub_status:<org_id>` whenever subscription or payment updates occur. | OPEN |

---

## 📋 P2 & P3 — Medium & Low Priority (Post-Launch Backlog)

* **P2-01 (Medium)**: Implement Redis rate limiting across multi-instance Railway workers.
* **P2-02 (Medium)**: Execute Locust load test simulating 250 concurrent candidates taking AI interviews.
* **P2-03 (Medium)**: Add dedicated TURN server credentials for symmetric NAT WebRTC rooms.
* **P3-01 (Low)**: Migrate remaining inline styles in React components to Tailwind utility classes.
* **P3-02 (Low)**: Add dark/light mode toggle persistence in `localStorage`.
