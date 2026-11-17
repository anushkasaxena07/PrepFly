# PREPFLY: SUPABASE ROW-LEVEL SECURITY & TRUSTED TENANT ARCHITECTURE
## Defense-in-Depth Relational Security Architecture

**Date:** November 17, 2026  
**Auditor:** Senior Full-Stack & Security Engineer (Antigravity)  
**Status:** **ARCHITECTURAL BLUEPRINT (READ-ONLY)**  

---

## 1. Architectural Problem Statement & Threat Model

### The Production Vulnerability:
Historically, web applications using Supabase initialize a single backend client using `SUPABASE_SERVICE_ROLE_KEY`. In PostgreSQL, the `service_role` has the `BYPASSRLS` attribute. This introduces two structural failure modes:
1. **Single-Layer Fragility:** If an application endpoint forgets `WHERE organization_id = ...` or has an IDOR bug, the database returns foreign tenant data without objection because RLS is completely bypassed.
2. **PostgREST Exposure:** If the Supabase REST endpoint is ever accessed directly with the `anon` key, any table without RLS (currently 83 tables) exposes all records to unauthenticated scrapers.

### The Solution:
A three-tier zero-trust security architecture:
1. **Application Tier:** Route guards and `TenantContext` compute authoritative claims from cryptographically verified JWT tokens.
2. **Session Context Tier:** Flask establishes trusted session variables (`SET LOCAL app.current_org_id = ...`) on every pooled transaction.
3. **Database RLS Tier:** A dedicated restricted database role (`prepfly_app_role`) without `BYPASSRLS` executes normal queries, enforced strictly by PostgreSQL Row-Level Security.

---

## 2. Restricted Database Role Design (`prepfly_app_role`)

```sql
-- 1. Create a dedicated non-superuser role without BYPASSRLS
CREATE ROLE prepfly_app_role WITH LOGIN PASSWORD 'secure_app_password';

-- 2. Strictly deny superuser, replication, and RLS bypass privileges
ALTER ROLE prepfly_app_role NOBYPASSRLS NOSUPERUSER NOREPLICATION;

-- 3. Grant schema usage and standard DML permissions only
GRANT USAGE ON SCHEMA public TO prepfly_app_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO prepfly_app_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO prepfly_app_role;

-- 4. Revoke DDL and destructive permissions
REVOKE CREATE ON SCHEMA public FROM prepfly_app_role;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon;
```

---

## 3. Trusted Identity & Session Context Bridge

Because PrepFly uses self-signed HS256 JWT tokens rather than frontend GoTrue auth, PostgreSQL needs to receive the authenticated user's claims securely on each query transaction.

### 3.1 SQL Helper Functions in `public`
```sql
-- Safely extract user ID from transaction configuration parameter
CREATE OR REPLACE FUNCTION current_app_user_id() RETURNS TEXT AS $$
    SELECT NULLIF(current_setting('app.current_user_id', true), '');
$$ LANGUAGE sql STABLE;

-- Safely extract user role from transaction configuration parameter
CREATE OR REPLACE FUNCTION current_app_user_role() RETURNS TEXT AS $$
    SELECT NULLIF(current_setting('app.current_user_role', true), '');
$$ LANGUAGE sql STABLE;

-- Safely extract organization ID from transaction configuration parameter
CREATE OR REPLACE FUNCTION current_app_org_id() RETURNS TEXT AS $$
    SELECT NULLIF(current_setting('app.current_org_id', true), '');
$$ LANGUAGE sql STABLE;
```

### 3.2 Flask Database Connection Adapter
When executing queries for a user request under `prepfly_app_role`, Flask sets session variables scoped to the local transaction:
```python
def execute_tenant_transaction(db_conn, tenant_context, sql_query, params):
    """
    Executes an application query with guaranteed PostgreSQL transaction context.
    Parameters are scoped to the current transaction and automatically reset on commit/rollback.
    """
    with db_conn.cursor() as cur:
        # Bind authoritative context derived from verified JWT
        cur.execute("SET LOCAL app.current_user_id = %s;", (tenant_context.user_id,))
        cur.execute("SET LOCAL app.current_user_role = %s;", (tenant_context.role,))
        cur.execute("SET LOCAL app.current_org_id = %s;", (tenant_context.org_id or "",))
        
        # Execute query under RLS enforcement
        cur.execute(sql_query, params)
        return cur.fetchall()
```

---

## 4. Policy Designs Across Table Categories

### 4.1 Tenant-Owned Tables (Strict Cross-College Isolation)
Tables: `admin`, `org_memberships`, `org_invites`, `admin_coding`, `admin_interviews`, `announcements`, `support_conversations`, `support_messages`, `question_sheets`.

```sql
-- Enable RLS and force it even for table owners
ALTER TABLE public.org_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.org_memberships FORCE ROW LEVEL SECURITY;

-- Org Admin Policy: Can view and manage records strictly within their own organization
CREATE POLICY "org_admin_tenant_isolation" ON public.org_memberships
    FOR ALL TO prepfly_app_role
    USING (
        current_app_user_role() IN ('admin', 'org_admin')
        AND organization_id = current_app_org_id()
    )
    WITH CHECK (
        current_app_user_role() IN ('admin', 'org_admin')
        AND organization_id = current_app_org_id()
    );

-- Student Policy: Can view their own membership only
CREATE POLICY "student_own_membership" ON public.org_memberships
    FOR SELECT TO prepfly_app_role
    USING (
        current_app_user_role() = 'candidate'
        AND user_id = current_app_user_id()
    );
```

### 4.2 Individual-Owned Tables (Student Privacy Guarantees)
Tables: `parsed_resumes`, `candidate_profiles`, `resume_scores`, `career_goals`, `mentor_conversations`, `mentor_messages`, `study_logs`, `plans`, `user_api_usage`, `user_api_spending_limits`.

```sql
ALTER TABLE public.parsed_resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parsed_resumes FORCE ROW LEVEL SECURITY;

-- Absolute Individual Privacy: ONLY the student owner can read or write their resume
CREATE POLICY "candidate_exclusive_resume_access" ON public.parsed_resumes
    FOR ALL TO prepfly_app_role
    USING (
        current_app_user_role() = 'candidate'
        AND user_id = current_app_user_id()
    )
    WITH CHECK (
        current_app_user_role() = 'candidate'
        AND user_id = current_app_user_id()
    );

-- College admins have ZERO policy on parsed_resumes. 
-- Any query executed by an org admin returns 0 rows automatically.
```

### 4.3 Shared Dual-Context Tables (Private Practice vs Assigned Assessment)
Tables: `sessions`, `interview_turns`, `interview_reports`, `coding_submissions`.

```sql
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions FORCE ROW LEVEL SECURITY;

-- 1. Candidate always has access to all their own sessions (private and institutional)
CREATE POLICY "candidate_all_own_sessions" ON public.sessions
    FOR ALL TO prepfly_app_role
    USING (
        current_app_user_role() = 'candidate'
        AND user_id = current_app_user_id()
    )
    WITH CHECK (
        current_app_user_role() = 'candidate'
        AND user_id = current_app_user_id()
    );

-- 2. College Admin can access sessions ONLY if explicitly linked to their institution
CREATE POLICY "org_admin_assigned_sessions_only" ON public.sessions
    FOR SELECT TO prepfly_app_role
    USING (
        current_app_user_role() IN ('admin', 'org_admin')
        AND organization_id IS NOT NULL
        AND organization_id = current_app_org_id()
    );

-- Crucial: When organization_id IS NULL, the second policy evaluates to FALSE.
-- College admins can NEVER see personal mock interviews.
```

### 4.4 Sensitive Tables (Revoked Client Access)
Tables: `users`, `super_admin`, `otps`, `otp_requests`, `password_reset_tokens`, `auth_logs`, `audit_logs`, `ai_configuration`, `payment`, `invoice`.

```sql
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users FORCE ROW LEVEL SECURITY;

-- Explicitly revoke all client and app-role permissions
REVOKE ALL ON public.users FROM anon;
REVOKE ALL ON public.users FROM prepfly_app_role;

-- Only service_role (used by audited internal backend authentication functions) can read/write
CREATE POLICY "service_role_auth_only" ON public.users
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);
```

---

## 5. Local Filesystem Uploads Security Audit

Filesystem uploads in `f_backend/uploads/` bypass database RLS, requiring strict application-level controls:

| Upload Directory | File Types Handled | Ownership & Access Verification | Path Traversal Protection |
|---|---|---|---|
| `uploads/` | PDF, DOCX resumes | Bound to authenticated JWT `user_id`. Cannot upload for foreign user (`HTTP 403`). | `werkzeug.utils.secure_filename` strips `../` and directory separators. |
| `uploads/sheets/` | Institutional problem sheets | Validates `role in ('admin', 'org_admin')` and binds to `organization_id`. | Prepended with random UUID: `sheet_{uuid4()}_{filename}`. |
| `uploads/feedback/`| PNG, JPEG screenshots | Validates authenticated session; filenames hashed. | Stored in dedicated subfolder; served with attachment disposition. |
| `uploads/support/` | Support attachments | Validates membership in support thread `organization_id`. | UUID prefixed; direct browsing disabled. |

---

## 6. Mathematical Demonstration of SQL Isolation

Consider two institutions:
- College A (`org_id = 'org_sunrise'`)
- College B (`org_id = 'org_horizon'`)
- Independent Candidate Priya (`user_id = 'cand_priya'`, `org_id = NULL`)

### Query Executed by College A Admin under `prepfly_app_role`:
```sql
BEGIN;
SET LOCAL app.current_user_id = 'admin_aditya';
SET LOCAL app.current_user_role = 'org_admin';
SET LOCAL app.current_org_id = 'org_sunrise';

-- Query attempting to dump all student memberships without a WHERE clause
SELECT id, organization_id, user_id FROM org_memberships;
```

### PostgreSQL Engine Evaluation:
1. `org_admin_tenant_isolation` policy applied: `organization_id = current_app_org_id()`
2. Engine translates query to: `SELECT ... WHERE organization_id = 'org_sunrise'`
3. Rows matching `org_horizon`: **FILTERED OUT (0 rows)**
4. Rows matching independent accounts: **FILTERED OUT (0 rows)**
5. Result: **Only Sunrise Peak student records returned.**

### Query Attempting to Read Student Resumes:
```sql
SELECT * FROM parsed_resumes WHERE user_id = 'cand_priya';
```
1. `candidate_exclusive_resume_access` policy applied: requires `current_app_user_role() = 'candidate'`
2. Actor has role `'org_admin'` $\rightarrow$ Policy evaluates to `FALSE`
3. Engine returns: **0 rows (Empty Set)**
4. Result: **College Admin cannot read candidate resume even with a raw SQL query.**
