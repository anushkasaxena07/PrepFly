# PrepFly Security Incident Remediation Checklist & Runbook
**Supabase Project Ref:** `liquygzrammcbsikirae`  
**Classification:** High Severity — Public RLS Exposure & Sensitive Column Remediation  
**Status:** Remediated in Code & Migrations — Awaiting Operational Key Rotation & SQL Execution  

---

## 1. Executive Summary & Threat Assessment
Prior to migration `20261118161500_enable_rls_lockdown.sql` (and `017_enable_rls_lockdown.sql`), tables in the `public` schema were configured without Row Level Security (RLS) enabled. PostgREST allowed direct HTTP queries using the Supabase Project URL and `anon` public API key.

Because tables were publicly reachable, **we must assume that existing credentials, active sessions, OTPs, password reset tokens, and sensitive configurations may have been enumerated or harvested.**

This checklist defines the required operational, cryptographic, and database steps to completely purge compromised state, rotate all secrets, and lock down the platform.

---

## 2. Immediate Database Remediation (Run in Supabase SQL Editor)

Connect to the Supabase Dashboard SQL Editor for project `liquygzrammcbsikirae` and execute the following commands:

```sql
-- STEP 2.1: Purge All In-Flight Authentication Secrets & Single-Use Tokens
TRUNCATE TABLE public.otps CASCADE;
TRUNCATE TABLE public.otp_requests CASCADE;
TRUNCATE TABLE public.password_reset_tokens CASCADE;

-- STEP 2.2: Apply RLS Lockdown Migration
-- Run the contents of supabase/migrations/20261118161500_enable_rls_lockdown.sql

-- STEP 2.3: Verify Zero Tables Without RLS (Expect 0 rows)
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' AND NOT rowsecurity;

-- STEP 2.4: Verify Anon and Authenticated Roles Have Zero Table Grants (Expect 0 rows)
SELECT grantee, table_schema, table_name, privilege_type 
FROM information_schema.role_table_grants 
WHERE table_schema = 'public' 
  AND grantee IN ('anon', 'authenticated');
```

---

## 3. Cryptographic Key & Secret Rotation

Because JWTs are verified using `JWT_SECRET_KEY`, rotating `JWT_SECRET_KEY` cryptographically invalidates 100% of all issued access tokens across all candidates, college admins, and super admins.

### 3.1 Environment Variables to Rotate Immediately:
| Environment Variable | Service / Location | Action Required |
|---|---|---|
| `JWT_SECRET_KEY` | Render / Railway / Local `.env` | Generate a new 64-character hex secret (`openssl rand -hex 32`) and update environment. |
| `SUPABASE_SERVICE_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard -> Project Settings -> API | Regenerate `service_role` secret in Supabase dashboard; update backend deployment. |
| `SUPABASE_ANON_KEY` | Supabase Dashboard -> Project Settings -> API | Rotate `anon` public key in Supabase dashboard. |
| `GEMINI_API_KEY` | Google AI Studio | Revoke exposed Gemini API keys; generate new key and update `GEMINI_API_KEY`. |
| `RAZORPAY_KEY_ID` & `RAZORPAY_KEY_SECRET` | Razorpay Dashboard -> Settings -> API Keys | Regenerate API keys in Razorpay; update deployment env vars. |
| `SMTP_PASSWORD` / `RESEND_API_KEY` | Email Provider (SendGrid/Resend/Gmail) | Rotate application password or API token; update deployment env vars. |

### 3.2 GitHub Actions Secrets to Update:
Update repository secrets under **GitHub Repository -> Settings -> Secrets and variables -> Actions**:
- `JWT_SECRET_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `GEMINI_API_KEY`
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `SMTP_PASSWORD`

---

## 4. Forced Password Reset & Identity Integrity Audit

### 4.1 Invalidate Passwords & Force Reset
Run the following SQL in Supabase SQL editor to force password re-authentication for all users:

```sql
-- Invalidate password hashes so users must use the 'Forgot Password' OTP flow to reset
-- (Alternatively, mark password_reset_required flag if added to schema)
UPDATE public.users 
SET password = 'FORCE_RESET_' || md5(random()::text || clock_timestamp()::text)
WHERE role = 'candidate';

-- For administrators and super_admins, manually set fresh temporary hashed passwords
-- or reset via Flask CLI / verified admin invite flow.
```

### 4.2 Inspect Administrative Accounts for Unauthorized Injections
Run the following queries to verify no unauthorized administrative accounts were created:

```sql
-- Check for unexpected super administrators
SELECT id, email, name, role, created_at 
FROM public.super_admin;

-- Check for unexpected organization administrators
SELECT id, organization_id, email, name, role, created_at 
FROM public.admin;

-- Check for unauthorized elevated privileges in users table
SELECT id, email, name, role, organization_id, created_at 
FROM public.users 
WHERE role IN ('ADMIN', 'SUPER_ADMIN', 'Organization Admin', 'recruiter');
```

---

## 5. Tampering Audit Across Business & Billing Tables

Query the database for unauthorized plan upgrades, altered spending limits, or injected subscriptions:

```sql
-- 5.1 Audit Subscription Table for Unauthorized Upgrades
SELECT s.id, s.user_id, s.organization_id, s.plan, s.status, s.created_at, u.email
FROM public.subscription s
LEFT JOIN public.users u ON s.user_id = u.id
ORDER BY s.created_at DESC;

-- 5.2 Audit Platform Plans for Price or Quota Tampering
SELECT id, plan_name, price, currency, duration_days, max_candidates 
FROM public.platform_plans;

-- 5.3 Audit AI Configuration & Platform Settings
SELECT * FROM public.ai_configuration;
SELECT * FROM public.platform_settings;

-- 5.4 Check User Spending Limits
SELECT * FROM public.user_api_spending_limits 
WHERE monthly_budget_usd > 100.0;
```

---

## 6. Access Logs & Forensic Review

1. **Supabase API Gateway Logs:**
   Navigate to **Supabase Dashboard -> Logs -> API Logs**:
   - Filter for `GET /rest/v1/users` or `GET /rest/v1/admin` with API key `anon`.
   - Identify unauthorized IP addresses that performed bulk exports.
2. **Backend Authentication Logs:**
   Inspect `auth_logs` table for abnormal failed/successful login attempts:
   ```sql
   SELECT ip_address, action, success, count(*) 
   FROM public.auth_logs 
   GROUP BY ip_address, action, success 
   ORDER BY count(*) DESC 
   LIMIT 50;
   ```
3. **Activity Logs:**
   Inspect `activity_logs` for suspicious administrative events:
   ```sql
   SELECT actor_id, actor_email, action, target_type, target_id, created_at 
   FROM public.activity_logs 
   ORDER BY created_at DESC 
   LIMIT 100;
   ```

---

## 7. Verification & Sign-off

- [ ] All database tables have `rowsecurity = true`.
- [ ] `anon` and `authenticated` have 0 privileges on schema `public`.
- [ ] Supabase Database Linter reports **0 errors** for `rls_disabled_in_public` (lint 0013).
- [ ] Supabase Database Linter reports **0 errors** for `sensitive_columns_exposed` (lint 0023).
- [ ] All environment secrets rotated in production hosting and GitHub Actions.
- [ ] In-flight tokens, OTPs, and sessions purged.
- [ ] Master CI pipeline passes cleanly on the staging branch.
