"""
Executes the RLS lockdown migration against an ephemeral disposable PostgreSQL 16 cluster.
Verifies:
  1. The migration applies cleanly without syntax or execution errors.
  2. Exactly 0 public tables have rowsecurity = false.
  3. Exactly 0 public tables have grants to anon or authenticated.
"""

import sys
import os
import tempfile

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    import pgserver
    HAS_PG_DEPS = True
except ImportError:
    HAS_PG_DEPS = False

MIGRATION_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "migrations",
    "017_enable_rls_lockdown.sql"
)

def test_rls_lockdown_on_postgres():
    if not HAS_PG_DEPS:
        print("[SKIP] psycopg2 or pgserver not installed in environment; skipping disposable postgres test.")
        return 0

    print("=" * 75)
    print("     TESTING RLS LOCKDOWN MIGRATION ON DISPOSABLE POSTGRESQL 16")
    print("=" * 75)

    temp_dir = tempfile.mkdtemp(prefix="pg_rls_lockdown_")
    server = pgserver.get_server(temp_dir)
    uri = server.get_uri()
    print(f"PostgreSQL 16 URI: {uri}")

    conn = psycopg2.connect(uri)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # 1. Create Supabase standard roles if not present
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'anon') THEN
                CREATE ROLE anon NOLOGIN;
            END IF;
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
                CREATE ROLE authenticated NOLOGIN;
            END IF;
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN
                CREATE ROLE service_role NOLOGIN BYPASSRLS;
            END IF;
        END $$;
    """)

    # 2. Create sample un-secured public tables to simulate the project's pre-lockdown state
    cur.execute("""
        CREATE TABLE IF NOT EXISTS public.users (id TEXT PRIMARY KEY, email TEXT, password TEXT);
        CREATE TABLE IF NOT EXISTS public.pending_users (id TEXT PRIMARY KEY, email TEXT, password TEXT);
        CREATE TABLE IF NOT EXISTS public.admin (id TEXT PRIMARY KEY, email TEXT, password TEXT);
        CREATE TABLE IF NOT EXISTS public.super_admin (id TEXT PRIMARY KEY, email TEXT, password TEXT);
        CREATE TABLE IF NOT EXISTS public.otps (id TEXT PRIMARY KEY, email TEXT, otp TEXT, expires_at TIMESTAMPTZ, is_used BOOLEAN);
        CREATE TABLE IF NOT EXISTS public.otp_requests (id TEXT PRIMARY KEY, email TEXT, created_at TIMESTAMPTZ);
        CREATE TABLE IF NOT EXISTS public.password_reset_tokens (id TEXT PRIMARY KEY, email TEXT, token TEXT, expires_at TIMESTAMPTZ, is_used BOOLEAN);
        CREATE TABLE IF NOT EXISTS public.feedback (id TEXT PRIMARY KEY, session_id TEXT, rating INT, message TEXT);
        CREATE TABLE IF NOT EXISTS public.coding_submissions (id TEXT PRIMARY KEY, session_id TEXT, passed INT, total INT);
        CREATE TABLE IF NOT EXISTS public.speech_analyses (id TEXT PRIMARY KEY, session_id TEXT, metrics TEXT);
        CREATE TABLE IF NOT EXISTS public.students (id TEXT PRIMARY KEY, name TEXT, email TEXT);
        CREATE TABLE IF NOT EXISTS public.organization (id TEXT PRIMARY KEY, name TEXT);
        CREATE TABLE IF NOT EXISTS public.skills (id TEXT PRIMARY KEY, name TEXT);

        -- Give anon and authenticated default privileges before migration
        GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
    """)

    # 3. Read and apply the lockdown migration
    with open(MIGRATION_PATH, "r", encoding="utf-8") as f:
        sql = f.read()

    print("Applying migration 017_enable_rls_lockdown.sql...")
    cur.execute(sql)
    print("Migration executed successfully!")

    # 4. Verify check 1: zero public tables with rowsecurity = false
    cur.execute("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' AND NOT rowsecurity;
    """)
    unprotected = cur.fetchall()
    print(f"Unprotected tables (expect 0): {len(unprotected)}")
    if unprotected:
        print(f"FAILED: Found unprotected tables: {unprotected}")
        sys.exit(1)

    # 5. Verify check 2: zero table privileges for anon or authenticated
    cur.execute("""
        SELECT table_name, grantee, privilege_type
        FROM information_schema.role_table_grants 
        WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated');
    """)
    grants = cur.fetchall()
    print(f"Privileges granted to anon/authenticated (expect 0): {len(grants)}")
    if grants:
        print(f"FAILED: Found lingering privileges: {grants}")
        sys.exit(1)

    cur.close()
    conn.close()
    server.cleanup()

    print("=" * 75)
    print(">>> DISPOSABLE POSTGRESQL 16 RLS LOCKDOWN VERIFICATION PASSED! <<<")
    print("=" * 75)


if __name__ == "__main__":
    test_rls_lockdown_on_postgres()
