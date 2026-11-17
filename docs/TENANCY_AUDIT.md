# PrepFly: College ↔ Student Linking and Strict Tenant Isolation Audit

**Date:** November 17, 2026  
**Auditor:** Senior Full-Stack & Security Engineering Lead  
**Branch:** `ai-inw`  
**Status:** Phase 0 Completed (Read-Only Audit)  

---

## Executive Summary

PrepFly serves three distinct personas:
1. **Super Admin**: Platform owner managing all organizations, plans, and platform-wide configurations.
2. **College / Organization Admin**: College representatives (e.g., Aditya representing Sunrise Peak / Stanford Tech Institute) managing their own students, assessments, and reports.
3. **Students**:
   - **College-linked students**: Students affiliated with a specific college who take college-assigned tests and interviews.
   - **Independent users**: Self-registered individuals who practice independently without college affiliation.

This audit evaluates the codebase against **Strict Multi-Tenancy and Isolation Invariants**. The audit confirms **critical tenant leaks, broken student linking, hardcoded tenant credentials, unscoped queries, and fake UI metrics**. 

All findings documented below represent observed code and schema realities in `f_backend/app.py`, `f_backend/local_supabase.py`, and `f_frontend/src/`.

---

## 1. Current Linking & Tenancy Architecture

### 1.1 Schema Breakdown: The Disconnected Student Tables

The system currently maintains two entirely disconnected representations of students:

```
+-----------------------------------+       +------------------------------------+
|               users               |       |              students              |
+-----------------------------------+       +------------------------------------+
| id (UUID / string)                |       | id (UUID / string)                 |
| email                             |       | name                               |
| password_hash                     |       | email                              |
| role ('candidate', 'ADMIN', etc.) |       | organization_id (foreign key text) |
| organization_id (TEXT, NULLABLE)  |       | current_year                       |
| created_at                        |       | target_role                        |
+-----------------------------------+       | readiness_score (float)            |
                                            | attendance_percentage (float)      |
                                            +------------------------------------+
```

#### Defect 1: Self-Registered Students Never Link to Colleges
When a student signs up via standard email registration (`/register`) or Google OAuth (`/auth/google/verify`):
- A row is inserted into `users` with `role = 'candidate'` and `organization_id = NULL`.
- No record is created in `students`.
- Result: Self-registered college students never appear in the College Admin portal.

#### Defect 2: Admin-Created Students Have No Authentication Credentials
When a College Admin adds a student via `POST /api/admin/student` (`app.py:7245-7286`):
- A row is inserted into `students` with `organization_id = org_id`.
- Synthetic scores are injected: `readiness_score: 8.0`, `attendance_percentage: 80.0`.
- **No corresponding row is created in `users`**, and no password or invite token is generated.
- Result: Admin-created students exist only as roster rows; the human student cannot log in, take tests, or see their college assignments.

#### Defect 3: Disconnected Data Models Cause Empty Dashboards
When a College Admin visits the Students page (`GET /api/admin/students`), the endpoint queries:
```python
supabase.table("students").select("*").eq("organization_id", org_id).execute()
```
Because real users registered in `users` have no `students` record, the college roster is empty (`[]`), showing "No students match the selected filters".

---

## 2. Tenancy Leak Hunt: Route-by-Route Security Audit

Every endpoint accessible by College Admins and Students was audited for authentication, authorization, tenant scoping, and data leakage.

| Method | Endpoint | Auth Required | Role Enforced | Tenant Scoping Mechanism | Client Input Vulnerability | Verdict | Evidence / Finding |
|---|---|---|---|---|---|---|---|
| `GET` | `/api/admin/dashboard` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | Header fallback | `X-Organization-Id` override | **CRITICAL LEAK** | If `students` table is empty for `org_id`, falls back to querying ALL users: `supabase.table("users").select("*").neq("role", "ADMIN").neq("role", "SUPER_ADMIN")` leaking global students across all colleges! |
| `POST` | `/api/admin/login` | None (Public) | None | Hardcoded | None | **HIGH VULN** | Hardcoded credentials: email `"admin@college.edu"` or `"aditya@college.edu"` bypasses password checks and returns hardcoded `org_id="d258e381-6a6e-4376-8bf2-2865731b1939"`. |
| `GET` | `/api/admin/students` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | Scoped by `org_id` | `X-Organization-Id` header | **VULNERABLE** | Relies on client-controlled `X-Organization-Id` header when JWT `org_id` is absent. Queries disconnected `students` table. |
| `POST` | `/api/admin/student` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | Scoped by `org_id` | `X-Organization-Id` header | **DEFECTIVE** | Inserts into `students` without creating `users` row. Injects hardcoded synthetic readiness/attendance. |
| `POST` | `/api/admin/students/import` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | None (Stub) | None | **FAKE STUB** | Returns `{"success": true, "imported_count": random.randint(5, 12)}`. Does not parse files or write to database. |
| `GET` | `/api/admin/interviews` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | Scoped by `org_id` | `X-Organization-Id` header | **SAFE (SCOPED)** | Properly scopes to `admin_interviews.eq("organization_id", org_id)`. Returns empty list `[]` when no interviews configured. |
| `POST` | `/api/admin/interviews` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | Injects `org_id` | `X-Organization-Id` header | **SAFE (SCOPED)** | Injects authenticated `organization_id` into created interview record. |
| `GET` | `/api/admin/interview-pdf/<id>` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | Scoped verification | ID path param | **LEAK VIA 403** | Returns HTTP 403 when interview belongs to another org. Violates Golden Rule 4: Must return 404 to prevent resource probing. |
| `GET` | `/api/admin/coding-tests` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | Scoped by `org_id` | `X-Organization-Id` header | **SAFE (SCOPED)** | Properly scopes to `admin_coding.eq("organization_id", org_id)`. Returns `[]` when empty. |
| `POST` | `/api/admin/coding-tests` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | Injects `org_id` | `X-Organization-Id` header | **SAFE (SCOPED)** | Injects authenticated `organization_id` into created coding challenge. |
| `GET` | `/api/admin/coding-test/<id>/leaderboard` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | Partial scope | ID path param | **CRITICAL LEAK** | Unscoped query on `coding_submissions`: queries `supabase.table("coding_submissions").select("*").execute()` without `organization_id` filter (`app.py:7628`). Leaks submissions from other colleges! Returns 403 instead of 404 on foreign test ID. |
| `GET` | `/api/admin/question-bank` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | Mixed scoping | `X-Organization-Id` header | **PARTIAL LEAK** | Queries `question_bank` with `or(organization_id.eq.{org_id},organization_id.is.null)`. System questions have null `organization_id`. Safe, but college questions lack strict isolation checks on updates. |
| `GET` | `/api/admin/announcements` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | Scoped by `org_id` | `X-Organization-Id` header | **SAFE (SCOPED)** | Properly scopes to `organization_id.eq.{org_id}`. |
| `POST` | `/api/admin/announcements` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | Injects `org_id` | `X-Organization-Id` header | **SAFE (SCOPED)** | Injects authenticated `org_id`. |
| `GET` | `/api/notifications` (Student) | JWT / Session | `candidate` | Mixed filter | None | **CRITICAL LEAK** | `app.py:8761`: queries `supabase.table("announcements").select("*").execute()` unscoped! Filters in memory; if `organization_id` is null or `"All"`, individual non-college users receive announcements intended for specific colleges. |
| `GET` | `/api/admin/reports` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | Scoped | `X-Organization-Id` header | **SAFE (SCOPED)** | Aggregates based on `students` table. Empty when `students` is empty. |
| `GET` | `/api/admin/analytics` | `@require_org_admin` | `ADMIN`, `SUPER_ADMIN` | Scoped | `X-Organization-Id` header | **SAFE (SCOPED)** | Computes statistics from college student set. Empty when `students` is empty. |

---

## 3. Fake-Data & Blank-Page Inventory (College Portal)

Audited across all 12 sidebar pages in `f_frontend/src/pages/Admin/`:

| Page / Component | Line Range | Fake Metric / Literal | Root Cause | Required Real Source |
|---|---|---|---|---|
| **Dashboard** (`Dashboard.jsx`) | 34-41 | `trend="+14% this month"`, `trend="+8% active"`, `trend="35% conversion"`, `trend="+24% YoY"`, `trend="+18% YoY"`, `trend="Grade A"`, `trend="86th Percentile"`, `trend="100% Dynamic"` | Hardcoded display strings in KPI card definitions. | Calculate actual period-over-period percentage change from `admin_interviews` and `coding_submissions`. Show `"N/A"` or `"—"` if no prior period data exists. |
| **Dashboard** (`Dashboard.jsx`) | 81-95 | Storage card: `stats?.storage_used_mb ?? 420`, `stats?.storage_total_gb ?? 10` | Hardcoded fallback literals fabricate 420 MB and 10 GB when API returns null. | Query real Supabase Storage usage for the tenant. If unmetered/untracked, show `"Not Tracked"`. |
| **Dashboard** (`Dashboard.jsx`) | 84, 91 | Plan & Status: `stats?.plan_name \|\| "Active (ENTERPRISE PLAN)"`, `stats?.system_status \|\| "Active Session"` | Hardcoded fallback strings. | Fetch real subscription plan from `organization.plan_tier` or display `"Standard"`. |
| **Dashboard** (`app.py:7061-7135`) | 7061-7135 | `if ai_interviews_cnt == 0: ai_interviews_cnt = 124`<br>`if coding_tests_cnt == 0: coding_tests_cnt = 86` | Backend fabricates 124 interviews and 86 tests if the real database count is 0! | Remove fabrication. Return actual count `0`. |
| **Dashboard** (`app.py:7100-7115`) | 7100-7115 | Fake chart curve: `"labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]` with hardcoded arrays `[12, 19, 32, ...]` | Backend returns hardcoded static arrays for monthly performance trends. | Query actual aggregated test/interview completion timestamps grouped by calendar month. Return empty series if 0. |
| **Dashboard** (`app.py:7120-7130`) | 7120-7130 | Fabricated activity feed: `"Rahul Sharma completed AI Technical Interview"` | Backend injects fake hardcoded student activity log items. | Query real `activity_logs` or real completed sessions scoped to `organization_id`. Show empty state if none. |
| **Navbar** (`Navbar.jsx`) | 8-13 | Notification dropdown: `"Ananya Patel scored 92% in System Design"`, `"Aarav Sharma completed Coding Assessment"` | Hardcoded fake notifications in React component state. | Connect to real college notifications API or show `"No new notifications"`. |
| **Navbar** (`Navbar.jsx`) | 105-119 | Security badge: `"Multi-Tenant Encrypted"` | Hardcoded decorative badge claiming unverified encryption guarantees. | Replace with genuine tenant context indicator showing active College Name and verified isolation status. |
| **Students** (`Students.jsx`) | 45-70 | Roster displays: "No students match the selected filters" | Students table is empty because `users` table self-signups are disconnected. | Implement unified `org_memberships` and student linking flow so real college students populate the roster. |
| **AI Interview** (`AIInterview.jsx`) | 114-142 | **BLANK PAGE BODY** when no interviews exist | `interviews.map(...)` renders nothing when `interviews == []`. Component lacks an empty state wrapper! | Add robust empty state: `<EmptyState title="No AI Interviews Scheduled" message="Create your first interview schedule to get started." />`. |
| **Coding Tests** (`Coding.jsx`) | 202-230 | **BLANK PAGE BODY** when no tests exist | `tests.map(...)` renders nothing when `tests == []`. Component lacks an empty state wrapper! | Add robust empty state: `<EmptyState title="No Coding Challenges" message="Create a coding assessment for your students." />`. |
| **AdminContainer** (`AdminDashboardContainer.jsx`) | 43-51 | Admin Profile: Defaults to `"Aditya"`, `"aditya20522113@gmail.com"`, `"org_default"` | Hardcoded fallback props in container if user state is empty. | Read strictly from authenticated admin session token. |
| **Import Modal** (`app.py:7305`) | 7305-7307 | CSV Import returns random count `5` to `12` | Mock implementation does zero parsing and zero DB insertion. | Implement real CSV parsing, validation, dry-run preview, and transactional `org_invites` / `org_memberships` creation. |

---

## 4. Root Cause of Blank Pages on AI Interviews and Coding Tests

When a College Admin navigates to **AI Interviews** (`/admin/interview`) or **Coding Challenges** (`/admin/coding`):
1. The backend endpoints (`GET /api/admin/interviews` and `GET /api/admin/coding-tests`) return an empty JSON array: `{"success": true, "interviews": []}` and `{"success": true, "tests": []}`.
2. In `AIInterview.jsx`:
   ```jsx
   <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
     {interviews.map((interview) => (
       <InterviewCard key={interview.id} interview={interview} ... />
     ))}
   </div>
   ```
   When `interviews` is `[]`, the grid renders 0 DOM elements.
3. In `Coding.jsx`:
   ```jsx
   <div className="space-y-4">
     {tests.map((test) => (
       <TestCard key={test.id} test={test} ... />
     ))}
   </div>
   ```
   When `tests` is `[]`, the container renders 0 DOM elements.
4. The page displays a header bar and search filters, followed by a completely blank white/dark void.
5. **Fix**: In both components, wrap the list rendering with:
   ```jsx
   {items.length === 0 ? (
     <EmptyState
       icon={...}
       title="No Assessments Yet"
       description="Create your first assessment to assign to your college students."
       actionLabel="Create Assessment"
       onAction={handleOpenCreateModal}
     />
   ) : (
     items.map(...)
   )}
   ```

---

## 5. Architectural Blueprint for Strict Multi-Tenancy

### 5.1 Unified Membership Architecture: `org_memberships`
To resolve the fundamental disconnect between `users` and `students`, we introduce a relational membership model:

```
+------------------------------------+
|               users                |  (Global identity, authentication, personal data)
+------------------------------------+
| id (UUID)                          |
| email                              |
| password_hash                      |
| role ('candidate', 'ADMIN', etc.)  |
+------------------------------------+
                 ^
                 | 1:N
+------------------------------------+
|          org_memberships           |  (Explicit tenant linkage with consent)
+------------------------------------+
| id (UUID)                          |
| organization_id (UUID -> org)      |
| user_id (UUID -> users)            |
| role ('student', 'admin', 'ta')    |
| status ('pending', 'active', etc.) |
| roll_number (TEXT)                 |
| department (TEXT)                  |
| joined_at (TIMESTAMPTZ)            |
+------------------------------------+
                 | N:1
                 v
+------------------------------------+
|           organizations            |  (Tenant entity)
+------------------------------------+
| id (UUID)                          |
| name ('Sunrise Peak College')      |
| join_code (6-char unique code)     |
| plan_tier ('starter', 'pro', etc.) |
| max_seats (INTEGER)                |
+------------------------------------+
```

### 5.2 Server-Derived Tenant Context (`TenantContext`)
Golden Rule 1 states: **Tenant identity comes from the server, never from the request.**
- Client header `X-Organization-Id` is rejected or ignored for scoping.
- The backend decorator `@require_org_admin` decodes the caller's JWT token, verifies their active membership in `org_memberships`, and injects `g.tenant_context = TenantContext(org_id=..., user_id=..., role=...)`.
- Every SQL query automatically binds `WHERE organization_id = g.tenant_context.org_id`.

### 5.3 Isolation of Independent Users
- Individual users who register without a college have **zero** active rows in `org_memberships`.
- Their private practice data (`interviews`, `coding_submissions`) has `organization_id IS NULL`.
- No College Admin can ever query records where `organization_id IS NULL` or `organization_id != admin.org_id`.

### 5.4 Cross-Tenant Status Code Standard: HTTP 404
In compliance with Golden Rule 4, any query attempting to fetch an entity belonging to another organization (e.g. `GET /api/admin/interview-pdf/<foreign_id>`) returns **HTTP 404 Not Found**, never 403 Forbidden. This completely eliminates resource-probing vulnerabilities.

---

## 6. Business Definition Questions (Batch for Approval)

Before proceeding to Phase 1 implementation, the following 7 business rules require explicit confirmation. Our recommended default is provided for each:

1. **Dual Membership vs. Single College Membership:**
   *Question:* Can a student belong to more than one college at the same time?  
   *Recommended Default:* **Single Active College Membership.** A student account can have at most one active college membership at any time (`status = 'active'`). If they join a new college, their previous membership is archived (`status = 'archived'`). This prevents cross-tenant data leakage and grading confusion.

2. **Personal Practice Data Privacy upon Joining a College:**
   *Question:* When an independent student joins a college via invite or join code, what happens to their historical individual practice data (interviews and coding sessions completed independently)?  
   *Recommended Default:* **Private and Isolated.** The college admin sees *only* assessments and interviews assigned by that college (`organization_id = college_org_id`). Historical independent practice (`organization_id IS NULL`) remains strictly private to the student and is never revealed to the college.

3. **Student Removal and Unlinking Behavior:**
   *Question:* What happens to a student's account and past submissions when a College Admin removes them from the roster?  
   *Recommended Default:* **Account Reverts to Independent; Historical College Records Preserved.** The student's account continues to exist as an independent user. Historical college test submissions remain archived in the college's audit log (read-only for accreditation), but the student loses access to future college-only tests.

4. **College Student Onboarding Mechanism:**
   *Question:* How should students join a college roster?  
   *Recommended Default:* **Dual Flow: Admin CSV Invite + Student Join Code with Consent.** 
   - Admin can upload a CSV to create pending invites (`org_invites`).
   - Alternatively, the College Admin provides a 6-character College Join Code (e.g. `SUN-2026`).
   - In both cases, the student must explicitly consent on login ("Join Sunrise Peak College? Your college admin will see your college test scores").

5. **Student Privacy in College Roster:**
   *Question:* Should College Admins see full student email addresses and roll numbers?  
   *Recommended Default:* **Full Roster Details Visible to Owning College; Zero Visibility to Other Colleges.** College admins require student names, emails, and college roll numbers for academic grading. Strict server-side scoping ensures this data is 100% invisible to any other tenant.

6. **Seat Entitlement Enforcement:**
   *Question:* How should the system respond when a College Admin attempts to add or invite students beyond their subscription seat limit (`max_seats`)?  
   *Recommended Default:* **Hard Ceiling with Clean Error.** The API rejects additions exceeding `max_seats` with HTTP 409 Conflict: `"Seat limit reached (100/100). Please upgrade your institutional plan to invite more students."`

7. **Storage Tracking on College Dashboard:**
   *Question:* How should the Dashboard "Storage Used" metric (`420 MB / 10 GB`) be calculated?  
   *Recommended Default:* **Aggregated Supabase Storage Buckets; Honest Empty State.** Compute real storage by summing `content_length` from Supabase Storage objects tagged with `organization_id`. If storage tracking is unmetered or not yet configured, display `"N/A (Standard Allocation)"` rather than a fake `420 MB`.

---

## 7. Phase 1–6 Overhaul Roadmap

- **Phase 1: Tenancy Data Model & Schema Migration**
  - Create reversible Migration `015_strict_tenant_isolation.sql`.
  - Introduce `org_memberships`, `org_invites`, and add `organization_id` to all tenant-owned entities.
  - Zero destructive changes; data integrity verified on local SQLite.

- **Phase 2: Strict Server-Side Enforcement Layer**
  - Implement `TenantContext` in `f_backend/services/tenancy.py`.
  - Strip client `X-Organization-Id` overrides; bind all queries to JWT-verified tenant.
  - Replace all cross-tenant 403 responses with 404 Not Found.
  - Fix unscoped queries in `coding_submissions` and `announcements`.

- **Phase 3: Student Linking & Roster Management Flows**
  - Build CSV import parser with preview, dry-run validation, and error reporting.
  - Implement 6-character College Join Code system with explicit student consent modal.
  - Unlink student endpoint with safe membership status archiving.

- **Phase 4: College Portal UI & Metrics Overhaul**
  - Remove all fake hardcoded metrics, smooth curves, and synthetic trend percentages from `Dashboard.jsx`.
  - Replace with genuine aggregate metrics from `MetricsService`.
  - Add robust `<EmptyState />` components to AI Interviews and Coding Challenges to eliminate blank pages.
  - Replace hardcoded Navbar notifications and unverified encryption badge with truthful tenant identity.

- **Phase 5: Student-Side Experience & Transparency**
  - Add "My College Affiliation" view on student profile.
  - Clear indicator showing "What my college can see" (college-assigned tests vs. private practice).
  - Scope student notifications to only include global or own-college announcements.

- **Phase 6: Multi-Tenant Verification & Automated Test Matrix**
  - Construct automated cross-tenant test suite (`test_strict_tenant_isolation.py`).
  - Test matrix: College A Admin, College B Admin, College A Student, College B Student, Independent Student.
  - Verify 0 leaks, 100% 404 on foreign resource access, and full reconciliation with Super Admin console.
