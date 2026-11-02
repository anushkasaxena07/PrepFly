# 🛡️ PrepFly Security Audit: Authentication, JWT Validation & Role-Based Authorization

**Date of Audit**: November 2026  
**Target System**: PrepFly SaaS Application (`f_backend`, `f_frontend`)  
**Auditor**: Principal Application Security Engineer  
**Status**: Comprehensive Verification & Remediation Complete  

---

## 1. Executive Summary

A comprehensive, code-level security audit was conducted across the **PrepFly** application, focusing specifically on:
1. **JWT Validation**: Cryptographic signature validation, algorithm enforcement, token expiration, audience verification (`aud`), claim integrity, identity derivation, and native compatibility with Supabase Authentication.
2. **Role-Based Access Control (RBAC)**: Privilege separation across Candidate (`candidate`), Organization Admin (`Organization Admin`), and Platform Super Admin (`SUPER_ADMIN`).
3. **Multi-Tenant Data Isolation**: Preventing cross-organization data leakage, Insecure Direct Object References (IDOR), and tenant spoofing via request bodies or query parameters.
4. **Privilege Escalation Resistance**: Validating registration flows, profile updates, and ensuring user-editable metadata (such as Supabase `user_metadata`) cannot grant administrative permissions.

All confirmed vulnerabilities have been remediated in source code and validated using automated regression tests and real cryptographic verification without mocking.

---

## 2. Findings & Classification Summary

| ID | Category | Description | Severity | Status |
| :--- | :--- | :--- | :---: | :---: |
| **SEC-01** | **JWT Validation** | Supabase Auth tokens with `aud: "authenticated"` caused audience rejection in PyJWT when decoding without explicit audience configuration. | **HIGH** | **VERIFIED FIXED** |
| **SEC-02** | **RBAC Authorization** | 16 Administrative API routes lacked `@require_org_admin` or `@require_admin`, allowing unauthenticated or candidate callers to access administrative endpoints. | **CRITICAL** | **VERIFIED FIXED** |
| **SEC-03** | **IDOR / Tenant Isolation**| `/api/admin/interview-pdf/<interview_id>` allowed cross-organization interview dossier access without verifying tenant ownership. | **HIGH** | **VERIFIED FIXED** |
| **SEC-04** | **IDOR / Tenant Isolation**| `/api/admin/reports/student/<student_id>/pdf` allowed cross-organization student dossier extraction without tenant validation. | **HIGH** | **VERIFIED FIXED** |
| **SEC-05** | **IDOR / Tenant Isolation**| `/api/admin/coding-test/<test_id>/leaderboard` did not verify if the coding assessment belonged to the admin's organization. | **MEDIUM** | **VERIFIED FIXED** |
| **SEC-06** | **Tenant Spoofing** | `/api/support/conversations` allowed Organization Admins to supply an arbitrary `organization_id` in request payloads. | **MEDIUM** | **VERIFIED FIXED** |
| **SEC-07** | **Metadata Escalation** | Potential role escalation if trusting Supabase `user_metadata.role` (which end-users can edit via Supabase client SDK). | **HIGH** | **VERIFIED FIXED** |
| **SEC-08** | **Account Integrity** | Profile update (`/update-profile`) permitted updating email without checking for collisions with existing user accounts. | **MEDIUM** | **VERIFIED FIXED** |
| **SEC-09** | **Configuration** | Backend required `JWT_SECRET_KEY` without recognizing the standard Supabase environment variable `SUPABASE_JWT_SECRET`. | **LOW** | **VERIFIED FIXED** |
| **SEC-10** | **Error Uniformity** | `require_org_admin` and `require_super_admin` swallowed expired token errors, returning generic 401/403 instead of `TOKEN_EXPIRED`. | **LOW** | **VERIFIED FIXED** |

---

## 3. Detailed Audit Findings & Implemented Fixes

### 3.1 SEC-01: Supabase & Flask Dual-Audience JWT Validation
* **Vulnerability Description**:  
  When Supabase Auth issues JWT access tokens, it embeds `aud: "authenticated"`. In contrast, tokens issued by the Flask backend omitted the `aud` claim. Calling standard `jwt.decode` with PyJWT resulted in an `InvalidAudienceError` on Supabase tokens if audience validation was enabled without `"authenticated"`, or raised `MissingRequiredClaimError` if `audience=["authenticated"]` was forced on Flask tokens.
* **Fix Implemented**:  
  In [`f_backend/app.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L93-L135), implemented `_decode_jwt`:
  - Peeks the unverified payload to check if `"aud"` is declared.
  - If `"aud"` is present, cryptographically validates against `ALLOWED_AUDIENCES = ["authenticated", "prepfly"]`. Any unrecognized audience (such as third-party application tokens) is rejected.
  - If `"aud"` is absent, validates signature, expiration, and enforces `HS256` without requiring the `aud` claim.
  - Verifies signatures using `_get_jwt_secret()`, supporting both `JWT_SECRET_KEY` and `SUPABASE_JWT_SECRET`.
* **Classification**: **VERIFIED FIXED**

---

### 3.2 SEC-02: Unprotected Administrative & Organization Endpoints
* **Vulnerability Description**:  
  Static AST inspection of all 106 admin and superadmin routes revealed that 16 organization administration routes in [`f_backend/app.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py) lacked `@require_org_admin` or `@require_admin` route decorators. Because they relied solely on `org_id = get_admin_org_id()`, unauthenticated callers or candidates calling these routes triggered queries with `organization_id=None` and returned mock data or executed database writes.
* **Affected Endpoints**:
  1. `/api/admin/interviews` & `/admin/interviews` (GET, POST)
  2. `/api/admin/interview-pdf/<interview_id>` & `/admin/interview-pdf/<interview_id>` (GET)
  3. `/api/admin/coding` & `/admin/coding` (GET, POST)
  4. `/api/admin/coding-test/<test_id>/leaderboard` (GET)
  5. `/api/admin/coding-test/<test_id>/export-csv` (GET)
  6. `/api/admin/question-bank` & `/admin/question-bank` (GET, POST)
  7. `/api/admin/question-bank/give/<q_id>` (POST)
  8. `/api/admin/reports` & `/admin/reports` (GET)
  9. `/api/admin/reports/generate` (POST)
  10. `/api/admin/reports/student/<student_id>/pdf` (GET)
  11. `/api/admin/analytics` & `/admin/analytics` (GET)
  12. `/api/admin/announcements` & `/admin/announcements` (GET, POST)
  13. `/api/admin/feedback-to-superadmin` (POST)
  14. `/api/admin/subscription` (GET)
  15. `/api/subscription/status` (GET)
  16. `/api/admin/settings` (GET, POST)
* **Fix Implemented**:  
  Applied `@require_org_admin` across all 16 endpoints. In addition, unified error handling in `_get_user_or_error()` ensures unauthenticated requests are rejected with HTTP 401 Unauthorized, and unauthorized candidates are rejected with HTTP 403 Forbidden.
* **Classification**: **VERIFIED FIXED**

---

### 3.3 SEC-03 & SEC-04: Cross-Organization IDOR in PDF Dossier Generation
* **Vulnerability Description**:  
  The endpoints `/api/admin/interview-pdf/<interview_id>` and `/api/admin/reports/student/<student_id>/pdf` retrieved records from `admin_interviews` and `students` using only primary keys (`id`), without verifying whether the record's `organization_id` matched the requesting administrator's tenant ID. An Organization Admin from College A could view candidates and interview dossiers from College B.
* **Fix Implemented**:  
  Added authoritative tenant ownership checks in both handlers:
  ```python
  if iv and org_id and iv.get("organization_id") and iv.get("organization_id") != org_id:
      p = getattr(request, "current_user", {})
      if p.get("role") != "SUPER_ADMIN":
          return jsonify({"error": "Forbidden: Cannot access interview from another organization"}), 403
  ```
  SuperAdmins retain legitimate multi-tenant oversight, while Organization Admins are strictly confined to their own tenant boundaries.
* **Classification**: **VERIFIED FIXED**

---

### 3.4 SEC-05 & SEC-06: Tenant Spoofing in Coding Leaderboards and Support Chat
* **Vulnerability Description**:  
  1. In `admin_coding_test_leaderboard(test_id)`, the test object was not verified against `organization_id`.
  2. In `handle_support_conversations`, the target organization was determined via `data.get("organization_id") or org_id`, allowing an Organization Admin to inject another organization's ID into the conversation.
* **Fix Implemented**:  
  1. Added database verification in `admin_coding_test_leaderboard` ensuring `test.organization_id == org_id` (unless the caller is SuperAdmin).
  2. In `handle_support_conversations`, restricted `target_org_id` override strictly to callers with role `"Super Admin"`; Organization Admins are locked to their token-derived `org_id`.
* **Classification**: **VERIFIED FIXED**

---

### 3.5 SEC-07: Protection Against User-Editable Metadata Escalation
* **Vulnerability Description**:  
  In Supabase Authentication, users can update their own `user_metadata` using `supabase.auth.updateUser({ data: { role: 'SUPER_ADMIN' } })`. If an application trusts `payload.get("user_metadata", {}).get("role")`, any candidate can elevate themselves to Super Admin.
* **Fix Implemented**:  
  In [`_normalize_jwt_payload`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L97-L122):
  - Elevated roles (`SUPER_ADMIN`, `ADMIN`, `Organization Admin`) are only accepted from top-level claims (issued directly by the backend) or `app_metadata.role` (which can only be modified by the backend using the Supabase Service Role key).
  - Any role specified in `user_metadata` is completely ignored for privilege determination, defaulting to `"candidate"`.
* **Classification**: **VERIFIED FIXED**

---

### 3.6 SEC-08: Profile Update Email Collision Guard
* **Vulnerability Description**:  
  `/update-profile` allowed updating `email` without verifying whether another user already owned that email address, creating potential collision risks.
* **Fix Implemented**:  
  Added a pre-update query in `/update-profile`:
  ```python
  exist_chk = supabase.table("users").select("id").eq("email", new_email).neq("id", user_id).execute()
  if exist_chk and exist_chk.data:
      return jsonify({"error": "Email already in use by another user"}), 400
  ```
* **Classification**: **VERIFIED FIXED**

---

### 3.7 SEC-09 & SEC-10: Secret Management & Unified Decorator Architecture
* **Vulnerability Description**:  
  Previously, decorators `require_org_admin` and `require_super_admin` swallowed expired token exceptions via `_get_optional_user()`, returning generic error codes instead of `TOKEN_EXPIRED`.
* **Fix Implemented**:  
  Implemented `_get_user_or_error()` which decodes and validates the token once, preserving specific error reasons:
  - Missing token -> 401 `"Authentication required"`
  - Expired token -> 401 `"Token has expired"` (`code: "TOKEN_EXPIRED"`)
  - Invalid audience -> 401 `"Invalid token audience"`
  - Bad signature / malformed -> 401 `"Invalid or expired token"`
  - Role mismatch -> 403 Forbidden with specific role requirement
* **Classification**: **VERIFIED FIXED**

---

## 4. Files Changed

1. [`f_backend/app.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py):
   - Added alternate `SUPABASE_JWT_SECRET` in `JWT_SECRET = _need(...)`.
   - Added `ALLOWED_AUDIENCES`, `_normalize_jwt_payload`, and `_decode_jwt`.
   - Unified auth decorators with `_get_user_or_error()`.
   - Added `@require_org_admin` to 16 administrative routes.
   - Added cross-organization IDOR checks to `admin_interview_pdf`, `admin_student_dossier_pdf`, and `admin_coding_test_leaderboard`.
   - Locked tenant ID derivation in `handle_support_conversations`.
   - Added email uniqueness collision check in `update_profile`.
2. [`f_backend/tests/test_jwt_rbac_security.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/tests/test_jwt_rbac_security.py):
   - Created new comprehensive 20-test security validation suite covering JWT validation, RBAC boundaries, cross-organization isolation, and privilege escalation prevention.
3. [`f_backend/tests/test_auth_isolation_security.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/tests/test_auth_isolation_security.py):
   - Aligned unauthenticated status assertion to accept standard 401/403.

---

## 5. Tests Executed & Actual Results

All tests were executed against the actual application code and database interfaces without mocking out authorization logic.

### 5.1 Test Suite Summary

| Test Suite | File | Tests Run | Result | Duration |
| :--- | :--- | :---: | :---: | :---: |
| **JWT & RBAC Security Suite** | `tests/test_jwt_rbac_security.py` | 20 | **20 PASSED (0 FAIL)** | 2.67s |
| **Auth & Tenant Isolation Suite** | `tests/test_auth_isolation_security.py` | 16 | **16 PASSED (0 FAIL)** | 0.40s |
| **Invoice Auth Regression Suite** | `tests/test_invoice_auth_regression.py` | 11 | **11 PASSED (0 FAIL)** | 1.12s |
| **Master Test Suite (All Modules)**| `run_all_tests.py` | 133 | **133 PASSED (0 FAIL)**| 29.03s |
| **Integration Test Runner** | `run_integration_tests.py` | 8 | **8 PASSED (0 FAIL)** | 16.22s |
| **Static Code Integrity** | `ruff check . --select F821,E9,F811` | - | **0 ERRORS** | 0.25s |
| **Frontend Production Build** | `npm run build` | 167 modules | **SUCCESS (0 ERRORS)**| 7.86s |

### 5.2 Specific Test Cases Verified

```text
[JWT Validation Tests]
  ✓ test_jwt_valid_flask_token_accepted               [200 OK]
  ✓ test_jwt_valid_supabase_token_accepted            [200 OK]
  ✓ test_jwt_user_metadata_role_escalation_ignored    [Role strictly normalized to 'candidate']
  ✓ test_jwt_invalid_signature_rejected               [401 Unauthorized]
  ✓ test_jwt_expired_token_rejected                   [401 Unauthorized with code=TOKEN_EXPIRED]
  ✓ test_jwt_malformed_token_rejected                 [401 Unauthorized across all malformed variants]
  ✓ test_jwt_untrusted_audience_rejected              [401 Unauthorized on foreign audience]
  ✓ test_jwt_missing_sub_claim_rejected               [401 Unauthorized on missing subject]

[RBAC & Privilege Escalation Tests]
  ✓ test_candidate_cannot_access_org_admin_apis       [403 Forbidden across all 20 tested admin routes]
  ✓ test_unauthenticated_cannot_access_org_admin_apis [401 Unauthorized across all tested routes]
  ✓ test_candidate_cannot_access_super_admin_apis     [403 Forbidden across 8 SuperAdmin routes]
  ✓ test_org_admin_cannot_access_super_admin_apis     [403 Forbidden across 5 SuperAdmin routes]
  ✓ test_role_escalation_via_update_profile_rejected  [403 Forbidden: Only Super Admin can assign roles]
  ✓ test_role_escalation_via_register_prevented       [Registered accounts forced to 'candidate']

[Multi-Tenant Cross-Organization Isolation Tests]
  ✓ test_org_admin_cannot_access_other_org_interview_pdf   [403 Forbidden]
  ✓ test_org_admin_cannot_access_other_org_student_dossier [403 Forbidden]
  ✓ test_org_admin_cannot_access_other_org_coding_lb       [403 Forbidden]
  ✓ test_superadmin_can_access_cross_org_resources         [200 OK for legitimate global oversight]

[Identity Derivation & Account Integrity Tests]
  ✓ test_candidate_cannot_update_another_user_profile [403 Forbidden]
  ✓ test_user_cannot_collide_or_takeover_existing_email [400 Bad Request]
```

---

## 6. Remaining Risks & Defense-in-Depth Considerations

While all identified application-level vulnerabilities have been fixed and verified in code, the following architectural considerations remain for production deployment:

1. **Token Storage in Frontend (`localStorage`)**:
   - Current: Access tokens are stored in browser `localStorage`.
   - Risk: If an XSS vulnerability occurs anywhere in third-party frontend dependencies, tokens stored in `localStorage` could be exfiltrated.
   - Recommendation: Transition to `HttpOnly`, `SameSite=Lax`, `Secure` cookies for refresh tokens or session state in future architectural iterations.
2. **Local Fallback DB in Development**:
   - Current: In development environments where Supabase DNS cannot be resolved, the application falls back to local SQLite.
   - Risk: In development, SQLite does not enforce PostgreSQL Row Level Security (RLS).
   - Protection: Production mode (`FLASK_ENV=production` or `RAILWAY_ENVIRONMENT`) strictly prohibits SQLite fallbacks and enforces live Supabase PostgreSQL connections.
3. **Secret Key Length in Production**:
   - Production validation: The application startup verifies `len(JWT_SECRET) >= 32` and aborts if test keys are used in production. Ensure that production secrets are managed via cloud secrets managers (e.g., Railway Secrets, Vercel Secrets).

---

## 7. Items Requiring Staging Verification

Because unit and integration tests run within an isolated test environment with deterministic fixtures, the following items must be verified in the staging environment before production rollout:

- [ ] **Live Supabase Auth Token Exchange**:
  Verify end-to-end token exchange using a live Supabase project instance with real users logging in via email/password and Google OAuth.
- [ ] **Supabase Service Role Key Protection**:
  Confirm that `SUPABASE_SERVICE_ROLE_KEY` is never exposed in client bundles (`VITE_` prefix must never be added to service keys).
- [ ] **Multi-Tenant Concurrent Admin Sessions**:
  Log in concurrently as Admin of College Alpha and Admin of College Beta in two separate browser sessions, verifying that real-time notifications and dashboard stats remain completely isolated under active websocket / long-polling traffic.
- [ ] **Staging Razorpay Webhook Signatures**:
  Test webhook receipt with Razorpay staging sandbox to ensure webhook HMAC signatures validate against `RAZORPAY_KEY_SECRET`.
- [ ] **Token Expiration Auto-Refresh**:
  Verify frontend token refresh interceptors gracefully refresh expired access tokens using Supabase refresh tokens without logging the candidate out mid-interview.

---

## 8. Conclusion

The security audit and remediation successfully eliminated:
- 1 critical vulnerability (missing authentication decorators on 16 admin routes).
- 4 high-severity vulnerabilities (cross-organization IDOR on PDF dossier generation, audience validation incompatibility with Supabase Auth, and potential role escalation via user-editable metadata).
- 3 medium-severity vulnerabilities (support chat tenant spoofing, coding leaderboard tenant isolation, and profile update email collision).

The PrepFly backend now implements a robust, unified, and cryptographically verified JWT validation and RBAC enforcement layer across all Candidate, Organization Admin, and Super Admin boundaries.
