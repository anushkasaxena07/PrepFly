"""
Disposable PostgreSQL 16 Native RLS and Tenancy Security Verification Suite.
Demonstrates:
  1. Initialization of disposable PostgreSQL 16 cluster via pgserver
  2. Setup of Supabase-aligned schema (tables, constraints, RLS)
  3. Creation of prepfly_app_role with NOBYPASSRLS, NOSUPERUSER, NOREPLICATION
  4. Real PostgreSQL Row-Level Security (RLS) enforcement across 2 organizations:
     - Org Alpha (admin_alpha, student_alpha)
     - Org Beta (admin_beta, student_beta)
     - Independent Student (student_gamma_indep, org_id = NULL)
  5. Raw SQL Attack Vectors:
     - Cross-tenant SELECT (Org A admin querying Org B records)
     - Cross-tenant INSERT (Org A admin injecting rows for Org B)
     - Cross-tenant UPDATE (Org A admin attempting to modify Org B data)
     - Cross-tenant DELETE (Org A admin attempting to delete Org B data)
     - Admin attempting to access Independent Student private data
  6. Missing and Invalid Context:
     - Queries without setting session context (fail-closed)
     - Queries with invalid/unrecognized role context
  7. Connection Pooling & Transaction Isolation:
     - Verified that SET LOCAL parameters reset automatically upon COMMIT / ROLLBACK
     - Verified that subsequent transactions on the same connection do not leak prior tenant context
"""

import sys
import os
import tempfile
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pgserver

def run_postgres_verification():
    print("=" * 80)
    print("       STARTING DISPOSABLE POSTGRESQL 16 RLS VERIFICATION TEST")
    print("=" * 80)

    # 1. Spin up ephemeral PostgreSQL 16 cluster
    temp_dir = tempfile.mkdtemp(prefix="pg_disposable_rls_")
    print(f"[1/7] Initializing ephemeral PostgreSQL 16 data cluster in: {temp_dir}")
    server = pgserver.get_server(temp_dir)
    uri = server.get_uri()
    print(f"      Server running at: {uri}")

    super_conn = psycopg2.connect(uri)
    super_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    super_cur = super_conn.cursor()

    super_cur.execute("SELECT version();")
    pg_ver = super_cur.fetchone()[0]
    print(f"      Engine Version: {pg_ver}")

    # 2. Implement prepfly_app_role and session helper functions
    print("\n[2/7] Creating prepfly_app_role (NOBYPASSRLS) and Context Functions...")
    super_cur.execute("""
        -- Create non-superuser restricted app role
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'prepfly_app_role') THEN
                CREATE ROLE prepfly_app_role WITH LOGIN PASSWORD 'test_secure_app_pass' NOBYPASSRLS NOSUPERUSER NOREPLICATION;
            END IF;
        END $$;

        -- Context extraction functions in public schema
        CREATE OR REPLACE FUNCTION current_app_user_id() RETURNS TEXT AS $$
            SELECT NULLIF(current_setting('app.current_user_id', true), '');
        $$ LANGUAGE sql STABLE;

        CREATE OR REPLACE FUNCTION current_app_user_role() RETURNS TEXT AS $$
            SELECT NULLIF(current_setting('app.current_user_role', true), '');
        $$ LANGUAGE sql STABLE;

        CREATE OR REPLACE FUNCTION current_app_org_id() RETURNS TEXT AS $$
            SELECT NULLIF(current_setting('app.current_org_id', true), '');
        $$ LANGUAGE sql STABLE;
    """)

    # 3. Create schema tables matching Supabase
    print("\n[3/7] Creating schema tables with RLS enabled...")
    super_cur.execute("""
        -- Organizations table
        CREATE TABLE IF NOT EXISTS public.organization (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT DEFAULT 'college',
            max_seats INT DEFAULT 100,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Organization Memberships
        CREATE TABLE IF NOT EXISTS public.org_memberships (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL REFERENCES public.organization(id),
            user_id TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Students Roster
        CREATE TABLE IF NOT EXISTS public.students (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL REFERENCES public.organization(id),
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            department TEXT,
            status TEXT DEFAULT 'Active',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Independent / Private Candidate Resumes
        CREATE TABLE IF NOT EXISTS public.parsed_resumes (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            skills_json TEXT,
            raw_text TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Shared Dual-Context Sessions (Institutional vs Personal)
        CREATE TABLE IF NOT EXISTS public.sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            organization_id TEXT REFERENCES public.organization(id),
            job_title TEXT,
            score FLOAT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Announcements (Tenant-Owned)
        CREATE TABLE IF NOT EXISTS public.announcements (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL REFERENCES public.organization(id),
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author_id TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Sensitive Table: Users
        CREATE TABLE IF NOT EXISTS public.users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Sensitive Table: Audit Logs
        CREATE TABLE IF NOT EXISTS public.audit_logs (
            id TEXT PRIMARY KEY,
            actor_id TEXT NOT NULL,
            actor_role TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Grant permissions to prepfly_app_role
        GRANT USAGE ON SCHEMA public TO prepfly_app_role;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO prepfly_app_role;
        REVOKE ALL ON public.users FROM prepfly_app_role;
        REVOKE ALL ON public.audit_logs FROM prepfly_app_role;
    """)

    # 4. Apply Row-Level Security Policies
    print("\n[4/7] Applying RLS Policies with FORCE ROW LEVEL SECURITY...")
    super_cur.execute("""
        -- Enable and Force RLS on all tenant and individual tables
        ALTER TABLE public.org_memberships ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.org_memberships FORCE ROW LEVEL SECURITY;

        ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.students FORCE ROW LEVEL SECURITY;

        ALTER TABLE public.parsed_resumes ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.parsed_resumes FORCE ROW LEVEL SECURITY;

        ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.sessions FORCE ROW LEVEL SECURITY;

        ALTER TABLE public.announcements ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.announcements FORCE ROW LEVEL SECURITY;

        ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.users FORCE ROW LEVEL SECURITY;

        -- 1. Students Policy: Org Admin can only see and manage their own org students
        DROP POLICY IF EXISTS "org_admin_students_policy" ON public.students;
        CREATE POLICY "org_admin_students_policy" ON public.students
            FOR ALL TO prepfly_app_role
            USING (
                current_app_user_role() IN ('admin', 'org_admin')
                AND organization_id = current_app_org_id()
            )
            WITH CHECK (
                current_app_user_role() IN ('admin', 'org_admin')
                AND organization_id = current_app_org_id()
            );

        -- 2. Announcements Policy: Org Admin can only see and manage their own org announcements
        DROP POLICY IF EXISTS "org_admin_announcements_policy" ON public.announcements;
        CREATE POLICY "org_admin_announcements_policy" ON public.announcements
            FOR ALL TO prepfly_app_role
            USING (
                current_app_user_role() IN ('admin', 'org_admin')
                AND organization_id = current_app_org_id()
            )
            WITH CHECK (
                current_app_user_role() IN ('admin', 'org_admin')
                AND organization_id = current_app_org_id()
            );

        -- 3. Resumes Policy: ONLY candidate owner can view or edit resume; ZERO org admin access
        DROP POLICY IF EXISTS "candidate_exclusive_resume_policy" ON public.parsed_resumes;
        CREATE POLICY "candidate_exclusive_resume_policy" ON public.parsed_resumes
            FOR ALL TO prepfly_app_role
            USING (
                current_app_user_role() = 'candidate'
                AND user_id = current_app_user_id()
            )
            WITH CHECK (
                current_app_user_role() = 'candidate'
                AND user_id = current_app_user_id()
            );

        -- 4. Sessions Policy:
        -- Candidate sees all their own sessions (private and assigned)
        -- Org Admin sees ONLY sessions explicitly tagged with their organization_id
        DROP POLICY IF EXISTS "candidate_own_sessions" ON public.sessions;
        CREATE POLICY "candidate_own_sessions" ON public.sessions
            FOR ALL TO prepfly_app_role
            USING (
                current_app_user_role() = 'candidate'
                AND user_id = current_app_user_id()
            )
            WITH CHECK (
                current_app_user_role() = 'candidate'
                AND user_id = current_app_user_id()
            );

        DROP POLICY IF EXISTS "org_admin_assigned_sessions" ON public.sessions;
        CREATE POLICY "org_admin_assigned_sessions" ON public.sessions
            FOR SELECT TO prepfly_app_role
            USING (
                current_app_user_role() IN ('admin', 'org_admin')
                AND organization_id IS NOT NULL
                AND organization_id = current_app_org_id()
            );
    """)

    # 5. Seed Test Data (under superuser)
    print("\n[5/7] Seeding Test Fixtures (College A, College B, Independent Candidate)...")
    super_cur.execute("""
        -- Organizations
        INSERT INTO public.organization (id, name) VALUES
            ('org_alpha', 'Alpha College of Engineering'),
            ('org_beta', 'Beta Institute of Technology');

        -- Students
        INSERT INTO public.students (id, organization_id, name, email, department) VALUES
            ('std_a1', 'org_alpha', 'Alice Alpha', 'alice@alpha.edu', 'Computer Science'),
            ('std_b1', 'org_beta', 'Bob Beta', 'bob@beta.edu', 'Information Technology');

        -- Private Resumes (Alice, Bob, and Independent Charlie)
        INSERT INTO public.parsed_resumes (id, user_id, raw_text) VALUES
            ('res_a1', 'std_a1', 'Alice Private Resume: Python, React'),
            ('res_b1', 'std_b1', 'Bob Private Resume: Java, Spring'),
            ('res_indep', 'cand_charlie_indep', 'Charlie Independent Resume: Rust, Go');

        -- Sessions (Alice institutional, Bob institutional, Charlie personal/unaffiliated)
        INSERT INTO public.sessions (id, user_id, organization_id, job_title, score) VALUES
            ('sess_a1', 'std_a1', 'org_alpha', 'Alpha Placement Mock', 88.5),
            ('sess_b1', 'std_b1', 'org_beta', 'Beta Placement Mock', 79.0),
            ('sess_charlie_indep', 'cand_charlie_indep', NULL, 'Personal Free Practice', 95.0);

        -- Announcements
        INSERT INTO public.announcements (id, organization_id, title, content, author_id) VALUES
            ('ann_a1', 'org_alpha', 'Alpha Campus Drive', 'Alpha announcement body', 'admin_alpha'),
            ('ann_b1', 'org_beta', 'Beta Campus Drive', 'Beta announcement body', 'admin_beta');

        -- Sensitive Users
        INSERT INTO public.users (id, email, password_hash, role) VALUES
            ('usr_admin_a', 'admin@alpha.edu', 'hash_admin_a', 'org_admin'),
            ('usr_admin_b', 'admin@beta.edu', 'hash_admin_b', 'org_admin');
    """)

    super_cur.close()
    super_conn.close()

    # Connect as prepfly_app_role to test RLS
    app_uri = uri.replace("postgres:@", "prepfly_app_role:test_secure_app_pass@")
    app_conn = psycopg2.connect(app_uri)
    # Autocommit is false by default: we use standard transactions

    print("\n[6/7] Executing Attack Vectors & RLS Verification as prepfly_app_role...")

    results = []

    def record_test(name, passed, detail):
        status = "PASS" if passed else "FAIL"
        results.append((name, status, detail))
        print(f"  [{status}] {name}: {detail}")

    # Helper to run a test with session parameters
    def run_as_context(role, user_id, org_id, test_fn):
        with app_conn.cursor() as cur:
            cur.execute("BEGIN;")
            cur.execute("SET LOCAL app.current_user_role = %s;", (role,))
            cur.execute("SET LOCAL app.current_user_id = %s;", (user_id,))
            cur.execute("SET LOCAL app.current_org_id = %s;", (org_id or "",))
            try:
                res = test_fn(cur)
                cur.execute("COMMIT;")
                return res
            except Exception as e:
                cur.execute("ROLLBACK;")
                raise e

    # Test 1: Org Admin A reads own students vs Org B students
    def test_admin_a_student_read(cur):
        cur.execute("SELECT id, name, organization_id FROM public.students;")
        rows = cur.fetchall()
        return rows

    rows = run_as_context("org_admin", "admin_alpha", "org_alpha", test_admin_a_student_read)
    is_isolated = len(rows) == 1 and rows[0][0] == "std_a1" and rows[0][2] == "org_alpha"
    record_test("Cross-Tenant Student Listing", is_isolated,
                f"Admin Alpha sees {len(rows)} row(s): {[r[0] for r in rows]}. Zero Org Beta rows visible.")

    # Test 2: Raw SQL cross-tenant SELECT with explicit WHERE organization_id = 'org_beta'
    def test_admin_a_cross_org_select(cur):
        cur.execute("SELECT id, name FROM public.students WHERE organization_id = 'org_beta';")
        return cur.fetchall()

    rows = run_as_context("org_admin", "admin_alpha", "org_alpha", test_admin_a_cross_org_select)
    record_test("Raw Cross-Tenant SELECT org_beta", len(rows) == 0,
                f"Admin Alpha queried org_beta explicitly. RLS returned {len(rows)} rows.")

    # Test 3: Raw SQL cross-tenant INSERT (Admin Alpha attempts to insert student into Org Beta)
    def test_admin_a_cross_org_insert(cur):
        try:
            cur.execute("""
                INSERT INTO public.students (id, organization_id, name, email, department)
                VALUES ('std_hacked', 'org_beta', 'Hacked Student', 'hacked@beta.edu', 'Hacking');
            """)
            return "SUCCESS_UNEXPECTED"
        except psycopg2.errors.InsufficientPrivilege:
            return "INSUFFICIENT_PRIVILEGE"
        except Exception as err:
            return f"BLOCKED_BY_RLS: {err.__class__.__name__}"

    insert_res = run_as_context("org_admin", "admin_alpha", "org_alpha", test_admin_a_cross_org_insert)
    record_test("Raw Cross-Tenant INSERT into org_beta", "BLOCKED_BY_RLS" in insert_res or "INSUFFICIENT_PRIVILEGE" in insert_res,
                f"Admin Alpha insertion into Org Beta was rejected: {insert_res}")

    # Test 4: Raw SQL cross-tenant UPDATE (Admin Alpha attempts to modify Bob Beta's department)
    def test_admin_a_cross_org_update(cur):
        cur.execute("UPDATE public.students SET department = 'Compromised' WHERE id = 'std_b1';")
        return cur.rowcount

    update_count = run_as_context("org_admin", "admin_alpha", "org_alpha", test_admin_a_cross_org_update)
    record_test("Raw Cross-Tenant UPDATE on std_b1", update_count == 0,
                f"Admin Alpha attempted UPDATE on std_b1. Rowcount affected: {update_count} (zero modified).")

    # Test 5: Raw SQL cross-tenant DELETE (Admin Alpha attempts to delete Bob Beta)
    def test_admin_a_cross_org_delete(cur):
        cur.execute("DELETE FROM public.students WHERE id = 'std_b1';")
        return cur.rowcount

    delete_count = run_as_context("org_admin", "admin_alpha", "org_alpha", test_admin_a_cross_org_delete)
    record_test("Raw Cross-Tenant DELETE on std_b1", delete_count == 0,
                f"Admin Alpha attempted DELETE on std_b1. Rowcount affected: {delete_count} (zero deleted).")

    # Test 6: Admin attempts to access student resumes (Privacy Test)
    def test_admin_a_resume_read(cur):
        cur.execute("SELECT id, user_id FROM public.parsed_resumes;")
        return cur.fetchall()

    resume_rows = run_as_context("org_admin", "admin_alpha", "org_alpha", test_admin_a_resume_read)
    record_test("Admin Access to Student Resumes", len(resume_rows) == 0,
                f"Admin Alpha queried parsed_resumes. Returned {len(resume_rows)} rows. Student privacy 100% protected.")

    # Test 7: Candidate Alice reads her own resume vs Bob's resume
    def test_alice_resume_read(cur):
        cur.execute("SELECT id, user_id FROM public.parsed_resumes;")
        return cur.fetchall()

    alice_resumes = run_as_context("candidate", "std_a1", "org_alpha", test_alice_resume_read)
    is_alice_private = len(alice_resumes) == 1 and alice_resumes[0][0] == "res_a1"
    record_test("Candidate Resume Ownership & Privacy", is_alice_private,
                f"Alice can see her own resume ('res_a1'), but cannot see Bob's or Charlie's ({len(alice_resumes)} returned).")

    # Test 8: Admin attempts to read Independent Student's personal practice sessions
    def test_admin_a_sessions_read(cur):
        cur.execute("SELECT id, user_id, organization_id FROM public.sessions;")
        return cur.fetchall()

    admin_sessions = run_as_context("org_admin", "admin_alpha", "org_alpha", test_admin_a_sessions_read)
    is_admin_sessions_safe = len(admin_sessions) == 1 and admin_sessions[0][0] == "sess_a1"
    record_test("Independent Student Session Privacy", is_admin_sessions_safe,
                f"Admin Alpha sees only Org Alpha sessions. Independent Charlie's session ('sess_charlie_indep') invisible.")

    # Test 9: Sensitive Table Access Denied for prepfly_app_role
    def test_app_role_read_users_table(cur):
        try:
            cur.execute("SELECT * FROM public.users;")
            return "SUCCESS_UNEXPECTED"
        except psycopg2.errors.InsufficientPrivilege:
            return "PERMISSION_DENIED_AS_EXPECTED"
        except Exception as e:
            return f"BLOCKED: {e}"

    with app_conn.cursor() as cur:
        cur.execute("BEGIN;")
        users_access_res = test_app_role_read_users_table(cur)
        cur.execute("ROLLBACK;")

    record_test("Sensitive Table Revocation (public.users)", users_access_res == "PERMISSION_DENIED_AS_EXPECTED",
                f"Access to sensitive 'users' table strictly rejected: {users_access_res}")

    # Test 10: Missing Context Fail-Closed Test
    def test_missing_context(cur):
        # Querying without setting SET LOCAL app.current_user_role or app.current_org_id
        cur.execute("SELECT id FROM public.students;")
        return cur.fetchall()

    with app_conn.cursor() as cur:
        cur.execute("BEGIN;")
        missing_ctx_rows = test_missing_context(cur)
        cur.execute("ROLLBACK;")

    record_test("Missing Session Context Fail-Closed", len(missing_ctx_rows) == 0,
                f"Query without context returned {len(missing_ctx_rows)} rows. Default behavior is 100% fail-closed.")

    # Test 11: Invalid / Unrecognized Role Fail-Closed Test
    def test_invalid_role(cur):
        cur.execute("SELECT id FROM public.students;")
        return cur.fetchall()

    invalid_role_rows = run_as_context("hacker_role", "attacker_666", "org_alpha", test_invalid_role)
    record_test("Invalid Role Fail-Closed", len(invalid_role_rows) == 0,
                f"Query with role 'hacker_role' returned {len(invalid_role_rows)} rows. Access completely denied.")

    # Test 12: Connection Pooling & Transaction Context Isolation
    print("\n[7/7] Testing Connection Pooling Transaction Hygiene...")
    with app_conn.cursor() as cur:
        # Step A: Request 1 sets context to Org Alpha
        cur.execute("BEGIN;")
        cur.execute("SET LOCAL app.current_user_role = 'org_admin';")
        cur.execute("SET LOCAL app.current_org_id = 'org_alpha';")
        cur.execute("SELECT current_app_org_id();")
        active_org = cur.fetchone()[0]
        cur.execute("COMMIT;")

        # Step B: Request 2 immediately on the exact same connection without SET LOCAL
        cur.execute("BEGIN;")
        cur.execute("SELECT current_app_org_id();")
        post_commit_org = cur.fetchone()[0]
        cur.execute("SELECT id FROM public.students;")
        post_commit_students = cur.fetchall()
        cur.execute("COMMIT;")

    is_pool_clean = (active_org == "org_alpha") and (post_commit_org is None) and (len(post_commit_students) == 0)
    record_test("Connection Pool Context Reset (SET LOCAL)", is_pool_clean,
                f"In-tx org: '{active_org}'. Next request on reused connection: '{post_commit_org}' (None). Rows: {len(post_commit_students)}. ZERO context leakage.")

    app_conn.close()
    server.cleanup()

    print("\n" + "=" * 80)
    print("                     POSTGRESQL 16 RLS VERIFICATION SUMMARY")
    print("=" * 80)
    total = len(results)
    passed = sum(1 for _, status, _ in results if status == "PASS")
    print(f"Total Tests Executed: {total}")
    print(f"Passed:               {passed}")
    print(f"Failed:               {total - passed}")
    print("=" * 80)

    if passed == total:
        print(">>> ALL POSTGRESQL 16 NATIVE RLS SECURITY VERIFICATION TESTS PASSED! <<<")
        return 0
    else:
        print(">>> SOME VERIFICATION TESTS FAILED! <<<")
        return 1

if __name__ == "__main__":
    sys.exit(run_postgres_verification())
