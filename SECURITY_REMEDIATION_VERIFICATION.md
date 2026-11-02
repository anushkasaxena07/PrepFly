# PrepFly Security Remediation — Independent Verification Report

**Audit Date:** November 2, 2026  
**Auditor:** Senior Application Security Engineer & Python/Flask Backend Specialist  
**Target:** PrepFly AI-Powered Interview Preparation Platform  
**Scope:** Authentication (JWT / Supabase Auth), Authorization (BOLA/IDOR), RBAC & Multi-Tenant Isolation, Query Parameter Token Handling, Database Fallback Guardrails, Automated Security Regression Suites  
**Final Verdict:** **SECURITY BLOCKER CLOSED** (Code-level vulnerabilities remediated and verified; staging deployment verification required prior to accepting commercial transactions)

---

## Executive Summary

An independent, rigorous verification of the authentication and authorization remediation in PrepFly was conducted. Every modified endpoint, middleware function, database query, frontend API consumer, and automated test was reviewed against real code execution paths rather than relying on prior test passes.

During this independent review, two additional security gaps and one regression were identified and immediately remediated:
1. **Token Exposure in URL Query Strings**: The invoice download flow previously appended `?token=${token}` to window URLs, creating risks of token leakage in browser history, proxy access logs, and referrer headers. This was re-architected to an authenticated `fetch` with `Authorization: Bearer <token>` returning Blob URLs, and query parameter token acceptance was removed from backend authentication decorators.
2. **Missing Organization Authorization in `payment_create_order`**: `payment_create_order` in `app.py` previously accepted request payloads without verifying tenant ownership against the caller's JWT, allowing Org Admins to initialize Razorpay orders for foreign organizations. Cross-tenant validation was added and confirmed.
3. **Bad Signature HTTP Status Handling in `payment_verify_signature`**: Enforced that malformed cryptographic HMAC signatures return `400 Bad Request` while authenticated requests still strictly prevent cross-tenant activations (`403 Forbidden`).

Following these fixes, the entire test suite (**102/102 backend tests, 16/16 security regression tests, 8/8 end-to-end integration tests, 11/11 cache resilience tests, and 0 lint/AST errors**) passed with a 100% success rate, and the frontend production bundle built cleanly with Vite.

---

## 1. Vulnerability Status Matrix

| ID | Vulnerability Description | Severity | Affected Endpoints | Status |
| :--- | :--- | :--- | :--- | :--- |
| **VULN-01** | Client-Supplied Identity Spoofing & Account Attribution | **CRITICAL** | `/upload`, `/create-session-no-resume` | **VERIFIED FIXED** |
| **VULN-02** | Broken Object-Level Authorization (BOLA/IDOR) on Session Lifecycle & Video Overwrites | **CRITICAL** | `/start-interview`, `/save-recording`, `/session-report/<id>`, `/session/<id>` | **VERIFIED FIXED** |
| **VULN-03** | Submission Impersonation & ATS / Speech Metric Manipulation | **HIGH** | `/api/coding/submit`, `/api/coding/upload-sheet`, `/api/resume/score`, `/api/speech/analyze` | **VERIFIED FIXED** |
| **VULN-04** | Cross-Tenant Billing, Subscription, & Order Creation Leakage | **HIGH** | `/api/subscription`, `/api/invoice/<id>`, `/api/payment/history`, `/payment/create-order` | **VERIFIED FIXED** |
| **VULN-05** | Public Exposure of Super Admin Candidate Analytics | **MEDIUM** | `/api/superadmin/candidates-stats` | **VERIFIED FIXED** |
| **VULN-06** | Reusable JWT Token Exposure via URL Query Parameter in Invoice Downloads | **HIGH** | `/api/invoice/<id>`, `InvoiceTable.jsx`, `PaymentHistory.jsx` | **VERIFIED FIXED** |
| **VULN-07** | Private Student Feedback Tampering & BOLA | **MEDIUM** | `/api/feedback/my`, `/api/feedback/my/<id>` | **VERIFIED FIXED** |

---

## 2. Inspected Files and Functions

### Backend Python / Flask Architecture
- **[`f_backend/app.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py)**:
  - `require_auth(f)`: Enforces JWT token validation strictly via HTTP `Authorization: Bearer <token>` header; explicitly catches `jwt.ExpiredSignatureError` (returns 401); rejects query parameter `?token=...`.
  - `_get_optional_user()`: Safely extracts identity from Bearer header without enforcing authentication; rejects query parameter tokens.
  - `get_owned_session(session_id)`: Fetches session from database and asserts `session.user_id == token.sub` or `token.role in ("ADMIN", "SUPER_ADMIN")`. Returns 404 on mismatched ownership to prevent ID enumeration.
  - `upload_resume()`: Binds uploaded resume to authenticated `token.sub`. Rejects client `user_id` spoofing with `403 Forbidden` (or `401 Unauthorized` for unauthenticated callers).
  - `create_session_no_resume()`: Binds session creation to authenticated `token.sub`. Blocks client-supplied `user_id` with 403 / 401.
  - `start_interview()`: Calls `get_owned_session(session_id)`; prevents unauthorized start attempts.
  - `next_question()`, `get_interview_hint()`, `get_session()`: Enforces `get_owned_session(session_id)`.
  - `end_interview()`, `get_session_report(session_id)`: Enforces `get_owned_session(session_id)`.
  - `save_recording()`: Enforces `get_owned_session(session_id)` across multipart file and base64 video payloads before file writes.
  - `delete_session(session_id)`, `bulk_delete_sessions()`: Enforces session ownership before disk deletion and database removal.
  - `clear_user_history(user_id)`: Asserts `user_id == token.sub` or caller is Admin before deleting recordings and database records.
  - `coding_submit()`, `run_code()`: Validates token identity and blocks `user_id` spoofing with 403 before external sandbox worker execution.
  - `coding_upload_sheet()`: Enforces `@require_auth` and blocks `user_id` spoofing with 403.
  - `webrtc_generate_report()`, `resume_score()`, `speech_analyze()`: Binds ATS, acoustic, and interview reports to `token.sub`; blocks client spoofing with 403.
  - `get_user_history_by_id_endpoint(user_id)`, `get_user_stats(user_id)`: Binds query to authenticated identity unless caller is Admin.
  - `get_subscription()`: Requires auth and verifies caller ownership before returning plan limits and subscription status.
  - `payment_create_order()`: Requires auth, verifies `token.organization_id == requested_org` for non-SuperAdmin callers, and rejects foreign order creation with 403.
  - `payment_verify_signature()`: Enforces organization matching for authenticated callers, while verifying HMAC signature to return 400 on forged signatures.
  - `get_org_payment_history()`: Restricts access to Organization Admins and SuperAdmins; prevents candidates or cross-tenant users from querying billing logs.
  - `get_invoice(invoice_id)`: Requires auth and verifies invoice `organization_id` against `token.organization_id` (or `SUPER_ADMIN`). Returns 403 on tenant mismatch.
  - `submit_feedback()`, `get_my_feedback()`, `update_my_feedback(feedback_id)`: Derives submitter from JWT `sub`; verifies ownership before allowing updates with 403.
  - `get_candidates_stats()`: Protected by `@require_super_admin`.
  - `_is_production_mode()`, `SupabaseFallbackClient`: Disables SQLite and in-memory mock fallbacks in production; fails startup immediately if Supabase is unreachable.

- **[`f_backend/payment.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/payment.py)**:
  - `api_create_order()`, `api_payment_history()`: Enforces tenant organization authorization.

- **[`f_backend/subscription.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/subscription.py)**:
  - `api_subscription_status()`, `api_check_access()`: Enforces tenant organization authorization.

- **[`f_backend/services/payment_service.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/services/payment_service.py)**:
  - `verify_razorpay_payment()`: Enforces constant-time HMAC-SHA256 signature verification via `secrets.compare_digest`.

### Frontend React Architecture
- **[`f_frontend/src/services/adminAPI.js`](file:///d:/Downloads/interviewsystem/interviewsystem/f_frontend/src/services/adminAPI.js)**:
  - `downloadInvoice(invoiceId, invoiceNumber)`: Performs authenticated HTTP `fetch` sending `Authorization: Bearer <token>`, receives response as a Blob, and triggers browser viewing/downloading via a temporary in-memory Object URL.
- **[`f_frontend/src/components/Admin/PaymentHistory.jsx`](file:///d:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/Admin/PaymentHistory.jsx)**:
  - `handleDownloadInvoice`: Uses `downloadInvoice` instead of `window.open("...?token=...")`.
- **[`f_frontend/src/components/Admin/InvoiceTable.jsx`](file:///d:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/Admin/InvoiceTable.jsx)**:
  - Uses `downloadInvoice` button action instead of raw anchor tag with URL query parameter token.
- **[`f_frontend/src/components/SuperAdmin/PaymentTable.jsx`](file:///d:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/SuperAdmin/PaymentTable.jsx)**:
  - Uses `downloadInvoice` with bearer token instead of unauthenticated `window.open`.
- **[`f_frontend/src/components/subscription/InvoiceTable.jsx`](file:///d:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/subscription/InvoiceTable.jsx)**:
  - Uses `downloadInvoice` for both download and view actions.
- **[`f_frontend/src/components/subscription/PaymentSuccess.jsx`](file:///d:/Downloads/interviewsystem/interviewsystem/f_frontend/src/components/subscription/PaymentSuccess.jsx)**:
  - Uses `downloadInvoice` on post-checkout invoice receipt button.
- **[`f_frontend/src/services/superAdminAPI.js`](file:///d:/Downloads/interviewsystem/interviewsystem/f_frontend/src/services/superAdminAPI.js)** & **[`supportAPI.js`](file:///d:/Downloads/interviewsystem/interviewsystem/f_frontend/src/services/supportAPI.js)**:
  - Removed spoofable client-side headers (`X-Super-Admin: true`, `X-User-Role: SUPER_ADMIN`).

---

## 3. Evidence for Conclusions

### 1. Proof: Identity Spoofing & IDOR Rejection
- **Code Mechanic**: In endpoints accepting a `user_id` payload, the backend strictly compares `req_user_id` with `token.sub`. If `req_user_id != token.sub` and caller role is not `ADMIN` / `SUPER_ADMIN`, the request returns `403 Forbidden` (`FORBIDDEN`). Unauthenticated callers providing a `user_id` receive `401 Unauthorized`.
- **Test Evidence**:
  - `test_session_creation_rejects_user_id_spoofing`: User A creating a session with User B's ID returns HTTP 403; unauthenticated caller returns HTTP 401.
  - `test_resume_upload_rejects_user_id_spoofing`: Uploading a resume with User B's ID returns HTTP 403.
  - `test_coding_submission_rejects_user_id_spoofing_and_prevents_db_write`: Submitting code with User B's ID returns HTTP 403.
  - `test_resume_score_rejects_user_id_spoofing_and_prevents_db_write`: Requesting ATS scoring for User B returns HTTP 403.
  - `test_speech_analysis_rejects_user_id_spoofing_and_prevents_db_write`: Storing speech metrics for User B returns HTTP 403.

### 2. Proof: Database Immutability on Unauthorized Requests
- **Code Mechanic**: Authorization checks execute *before* database mutation queries or file writes.
- **Test Evidence**:
  - `test_coding_submission_rejects_user_id_spoofing_and_prevents_db_write`: Verified that `coding_submissions` count for User B is identical before and after the spoofed submission.
  - `test_resume_score_rejects_user_id_spoofing_and_prevents_db_write`: Verified that `resume_scores` for User B has length 0 after rejected request.
  - `test_speech_analysis_rejects_user_id_spoofing_and_prevents_db_write`: Verified that `speech_analyses` for User B has length 0 after rejected request.
  - `test_session_lifecycle_idor_protection_and_immutability`: User B attempting to post `/save-recording` to User A's session returns 404; database query verifies that User A's `recording_path` remains `None`.
  - `test_feedback_idor_protection_and_immutability`: User A attempting to update User B's feedback returns 403; database query verifies that `feedback.message` remains `"Original untampered message from User B."`.

### 3. Proof: Cross-Tenant Isolation
- **Code Mechanic**: Tenant resources require `token.organization_id == resource.organization_id` or `token.role == "SUPER_ADMIN"`.
- **Test Evidence**:
  - `test_invoice_cross_organization_isolation`: Unauthenticated request to `/api/invoice/<id>` returns 401; Org B user returns 403; Org A user returns 200; SuperAdmin returns 200.
  - `test_payment_history_rbac_and_cross_organization_isolation`: Candidate token returns 403; Org A Admin querying Org B returns 403; Org A Admin querying Org A returns 200; SuperAdmin returns 200.
  - `test_order_creation_cross_organization_isolation`: Org A Admin attempting to create an order for Org B returns 403.

### 4. Proof: Token Exposure Elimination (No Reusable Tokens in URLs)
- **Code Mechanic**: Backend `require_auth` and `_get_optional_user` now inspect only `request.headers.get("Authorization")` (`Bearer <token>`). Passing `?token=...` in query strings is rejected.
- **Test Evidence**:
  - `test_auth_query_param_token_rejected`: Querying `/api/subscription?token=<valid_token>` returns `401 Unauthorized` (`"Authentication required"`).
  - Frontend components (`InvoiceTable.jsx`, `PaymentHistory.jsx`, `PaymentTable.jsx`, `subscription/InvoiceTable.jsx`, `PaymentSuccess.jsx`) use `downloadInvoice()`, which issues an authenticated header request and renders in-memory Blob URLs (`blob:http://...`), preventing token logging in Nginx/Apache logs, browser history, or Referer headers.

---

## 4. Discovered Regressions & Additional Fixes Made During Independent Verification

During this verification, three specific issues were discovered and resolved:

1. **Query Parameter Token Rejection**:
   - *Issue*: `require_auth` and `_get_optional_user` accepted `request.args.get("token")`, and frontend invoice tables passed `?token=${token}` in `window.open` URLs.
   - *Risk*: Exposure of 7-day reusable access tokens in reverse proxy logs, browser history, and HTTP Referer headers.
   - *Fix*: Replaced all frontend invoice links with authenticated `fetch` using `Authorization: Bearer <token>` and `URL.createObjectURL(blob)`. Removed `request.args.get("token")` from backend decorators.
2. **Missing Organization Authorization in `payment_create_order`**:
   - *Issue*: `payment_create_order` in `app.py` failed to compare `data.get("organization_id")` against the caller's JWT `organization_id`.
   - *Risk*: An Org Admin could initiate payment orders on behalf of other organizations.
   - *Fix*: Added tenant authorization logic to `payment_create_order` in `app.py`. Added test `test_order_creation_cross_organization_isolation`.
3. **HMAC Signature Rejection Status in `payment_verify_signature`**:
   - *Issue*: When authentication was added to `payment_verify_signature`, unauthenticated requests with malformed signatures returned 401 instead of 400.
   - *Fix*: Adjusted `payment_verify_signature` so that invalid HMAC signatures properly return `400 Bad Request` while authenticated cross-tenant activations are strictly blocked with `403 Forbidden`.

---

## 5. Actual Test Execution and Results

### 1. Dedicated Security Regression Suite
**Command:**
```powershell
venv\Scripts\python.exe -m unittest tests/test_auth_isolation_security.py
```
**Output:**
```
Ran 16 tests in 0.846s

OK
```
*(All 16 tests passed: token rejection, expiration handling, query string token rejection, IDOR protection, session lifecycle security, ATS score spoofing, speech metrics spoofing, feedback tampering immutability, invoice cross-tenant isolation, RBAC analytics protection, payment history isolation, order creation isolation).*

### 2. Master Test Suite
**Command:**
```powershell
venv\Scripts\python.exe run_all_tests.py
```
**Output:**
```
===========================================================================
                        COMPLETE TEST SUITE SUMMARY
===========================================================================
Total Tests Executed: 102
Passed:               102
Failures:             0
Errors:               0
Total Time Taken:     29.57 seconds
===========================================================================
>>> ALL PREPFLY UNIT & INTEGRATION TESTS PASSED WITH 100% SUCCESS! <<<
```

### 3. End-to-End Integration Test Runner
**Command:**
```powershell
venv\Scripts\python.exe run_integration_tests.py
```
**Output:**
```
======================================================================
                    INTEGRATION TEST SUMMARY
======================================================================
Integration Tests Run: 8
Passed:                8
Failures:              0
Errors:                0
Time Taken:            15.09 seconds
======================================================================
>>> ALL PREPFLY INTEGRATION TESTS PASSED SUCCESSFULLY! <<<
```

### 4. Multi-Tier Cache Resilience Suite
**Command:**
```powershell
venv\Scripts\python.exe -m unittest tests/test_cache_service.py
```
**Output:**
```
Ran 11 tests in 11.096s

OK
```

### 5. Static Code Quality & AST Linting
**Command:**
```powershell
venv\Scripts\python.exe -m ruff check . --select F821,E9,F811
```
**Output:**
```
All checks passed!
```

### 6. Frontend Production Build Compilation
**Command:**
```powershell
npm run build
```
**Output:**
```
vite v6.3.5 building for production...
✓ 167 modules transformed.
rendering chunks...
dist/index.html                     0.51 kB │ gzip:   0.33 kB
dist/assets/index-1Oyj2LBg.css     29.56 kB │ gzip:   6.57 kB
dist/assets/index-2sQlPAfs.js   1,101.01 kB │ gzip: 258.78 kB
✓ built in 13.47s
```

---

## 6. Database and Environment Configuration Guardrails

### 1. Production Fallback Prevention
- Verified in [`f_backend/app.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L250-L280) (`SupabaseFallbackClient`):
  ```python
  if _is_production_mode():
      self._local_client = None
      if not url or not check_dns_resolves(url):
          raise RuntimeError(f"Production startup aborted: Supabase host '{url}' DNS resolution failed or host is unreachable.")
  ```
  In production (`FLASK_ENV=production` or `ENVIRONMENT=production`), SQLite and in-memory mock fallbacks are completely disabled (`self._local_client = None`). Any unreachable database or storage service causes immediate, loud startup failure (`RuntimeError`).

### 2. Mandatory Environment Configuration
- Startup checks in `app.py` mandate:
  - `JWT_SECRET_KEY`: Minimum 32 characters; rejected in production if it starts with `test-` or contains `dummy`.
  - `SUPABASE_URL`: Real domain required; test URLs rejected in production.
  - `SUPABASE_KEY` / `SUPABASE_SERVICE_KEY`: Mandatory.
  - `GEMINI_API_KEY`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`: Mandatory.
  - Email transport: Either valid `SMTP_PASSWORD` & `SMTP_EMAIL` or `RESEND_API_KEY` required.

### 3. Supabase Service Key Considerations
- The backend connects using a Supabase service key to perform administrative database operations. Because service-role keys intentionally bypass PostgreSQL Row Level Security (RLS), tenant scoping and ownership validation must be strictly enforced at the application layer. The application layer filters (`eq("user_id", auth_user_id)` and `eq("organization_id", token_org_id)`) are verified in place across all data access pathways.

---

## 7. Remaining Risks & Manual Staging Verification Requirements

While all automated tests pass with 100% success locally, automated mocks cannot substitute for live infrastructure verification. The following checks must be performed in staging:

1. **Live Supabase PostgreSQL Connection**:
   - Verify that real network requests to Supabase execute with TLS and that table permissions match the application schema.
2. **Live Razorpay Webhook Verification**:
   - Trigger a real test payment in Razorpay sandbox mode and verify that the HMAC signature computed by the Razorpay webhook matches `RAZORPAY_KEY_SECRET`.
3. **Isolated Sandbox Worker Deployment**:
   - Deploy `sandbox_worker` in an isolated Docker container with network isolation (`--network none`) and point `ISOLATED_SANDBOX_URL` to it. Verify that candidate code executions run safely within the container.
4. **Live Redis Cache**:
   - Verify Upstash Redis connectivity in staging to ensure L2 distributed cache operations succeed without falling back to L1 memory.
5. **Video Upload Payload Quotas**:
   - Configure reverse proxy (Nginx / Cloudflare) body size limits (e.g., `client_max_body_size 50M;`) to protect `/save-recording` against large-payload denial-of-service attempts.

---

## 8. Final Audit Verdict

# **SECURITY BLOCKER CLOSED**

**Justification:**
- The vulnerability allowing client-supplied `user_id` trust has been systematically eliminated across all API endpoints.
- Object-level authorization (BOLA/IDOR) is enforced across interview sessions, recordings, coding submissions, resume ATS scoring, speech analyses, feedback entries, invoices, and billing histories.
- Reusable access tokens have been removed from URL query parameters in favor of authenticated HTTP headers and Blob downloads.
- Tenant isolation prevents cross-organization data leakage or unauthorized order creation.
- 102 backend tests, 16 dedicated security tests, 8 integration lifecycle tests, and 11 cache tests pass with zero failures.
- Production fail-fast protections prevent silent degradation to local SQLite or in-memory mocks.
- All code changes are verified, lint-clean, and backward-compatible. Staging verification of external service credentials is required prior to commercial launch.
