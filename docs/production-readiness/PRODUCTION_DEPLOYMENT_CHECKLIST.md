# 🚀 PrepFly Production Deployment Checklist (`PRODUCTION_DEPLOYMENT_CHECKLIST.md`)

Use this comprehensive verification checklist before releasing any production build or enabling commercial customer traffic on PrepFly.

---

## 1. Environment Variables & Secrets Validation

- [ ] **`FLASK_ENV=production`**: Enforced on Railway to permanently disable the local SQLite fallback and debug mode.
- [ ] **`JWT_SECRET_KEY`**: Cryptographically random 64-character hex string (minimum 32 characters; rejected if starts with `test-` or contains `dummy`).
- [ ] **`SUPABASE_URL`**: Points to live production Supabase instance (`https://atfozkznxxuehyjgqvvm.supabase.co`).
- [ ] **`SUPABASE_SERVICE_KEY`**: High-privilege service role key configured securely in Railway environment secrets (never committed to git).
- [ ] **`GEMINI_API_KEY` & Domain Keys**: Rotated production Gemini API keys active (`GEMINI_INTERVIEW_KEY`, `GEMINI_REPORT_KEY`, `GEMINI_CODING_KEY`).
- [ ] **`ISOLATED_SANDBOX_URL`**: Configured to `http://127.0.0.1:5050` or internal container DNS.
- [ ] **`ISOLATED_SANDBOX_SECRET`**: Minimum 32-character shared secret matching the worker container's secret.
- [ ] **`RAZORPAY_KEY_ID` & `RAZORPAY_KEY_SECRET`**: Production merchant live keys configured (starting with `rzp_live_`).
- [ ] **`SMTP_PASSWORD` / `RESEND_API_KEY`**: Production transactional email credentials active for OTP dispatch.
- [ ] **`FRONTEND_URL`**: Set strictly to `https://prepfly.vercel.app` (no wildcard `*` CORS in production).
- [ ] **`SENTRY_DSN`**: Sentry project DSN configured for real-time error tracking.

---

## 2. Database & Data Integrity

- [ ] **Supabase PostgreSQL Schema Migrations**: All 19 tables from [`supabase_schema.sql`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/supabase_schema.sql) applied to production PostgreSQL.
- [ ] **Foreign Key & Index Verification**: B-tree indexes created on `sessions.user_id`, `students.organization_id`, and `payment.razorpay_payment_id`.
- [ ] **Automated Backups Active**: Point-in-time recovery (PITR) and daily automated snapshots enabled in Supabase dashboard.
- [ ] **Connection Pooling**: Transaction mode connection pooler (port 6543) active to handle concurrent Gunicorn worker threads.
- [ ] **Production Startup Verification**: Backend starts cleanly without `[WARNING] Using local SQLite fallback database`.

---

## 3. Frontend Build & Domain Configuration

- [ ] **Vite Production Bundle Build**:
  ```bash
  cd f_frontend
  npm run build
  ```
  *(Must exit with code 0 without type or syntax errors).*
- [ ] **Environment Injection**: `VITE_BACKEND_URL=https://prepfly.up.railway.app` configured in Vercel project settings.
- [ ] **No Hardcoded Localhost URLs**: Static grep check verifies zero instances of `http://localhost:5000` in `dist/`.
- [ ] **HTTPS Enforced**: Automatic SSL/TLS certificates active with HTTP → HTTPS redirection on Vercel.
- [ ] **Content Security Policy (CSP)**: Headers configured to restrict script injection and unauthorized iframe embedding.

---

## 4. Code Execution Sandbox Infrastructure

- [ ] **Container Deployment**: Docker container `prepfly-sandbox-worker` running and healthy.
- [ ] **Unprivileged User**: Container process running under `UID 10001` (`sandboxuser`).
- [ ] **Read-Only Root Filesystem**: `read_only: true` with ephemeral `tmpfs` mounts on `/tmp` and `/app/scratch`.
- [ ] **Resource Limits Enforced**:
  - `limits.cpus: "2.0"`
  - `limits.memory: "512M"`
  - `limits.pids: 100`
- [ ] **Network Isolation**: Docker network configured with `internal: true` (outbound public internet blocked from worker).
- [ ] **Port Binding**: Port 5050 bound strictly to loopback `127.0.0.1:5050` (never exposed to public internet).
- [ ] **Health Endpoint Check**: `curl -s http://127.0.0.1:5050/health` returns status `healthy`.

---

## 5. Billing & Payment Gateway Setup

- [ ] **Razorpay Live Merchant Mode**: Account activated and KYC completed.
- [ ] **Webhook Endpoint Configured**:
  - URL: `https://prepfly.up.railway.app/api/payment/webhook`
  - Active Events: `order.paid`, `payment.captured`, `payment.failed`
  - Secret: Configured and matching `RAZORPAY_KEY_SECRET`.
- [ ] **GST & Invoice Compliance**: Generated invoices display valid sequential invoice numbering, 18% GST calculation, and official business address.
- [ ] **Live Sandbox Test**: Zero-dollar / test transaction validated in staging before opening merchant checkout.

---

## 6. AI Engine & Token Cost Controls

- [ ] **Model Initialization**: Verified that `gemini-2.5-flash` initializes cleanly without 404/400 errors.
- [ ] **Fallback Question Banks Active**: Verified that network interruptions gracefully fallback to curated offline questions.
- [ ] **Multi-Tier Caching Active**: Verified that identical question hints hit L1 cache in <1ms (`GET /api/cache/stats`).
- [ ] **Spending Ceilings**: Hard spending quota set in Google Cloud Console budget alerts ($50 / $200 / $500 thresholds).

---

## 7. Legal, Privacy & Customer Trust

- [ ] **Privacy Policy Published**: Publicly accessible at `/privacy` detailing data processing, storage, and retention.
- [ ] **Terms of Service Published**: Publicly accessible at `/terms` covering acceptable use and placement preparation disclaimers.
- [ ] **Refund & Cancellation Policy**: Clearly states subscription renewal, cancellation, and refund conditions.
- [ ] **DPDP Act (2023) Notice**: Explicit consent collected on candidate registration for resume parsing and voice analysis.
- [ ] **Support Channel Configured**: Monitored support email (`support@prepfly.io`) active and receiving incoming queries.

---

## 8. Deployment Smoke Tests

Execute these verification commands immediately following production deployment:

```bash
# 1. API Health Check
curl -f https://prepfly.up.railway.app/health
# Expected: {"status": "ok", "timestamp": "..."}

# 2. Multi-Tier Cache Verification
curl -f https://prepfly.up.railway.app/api/cache/stats
# Expected: {"status": "healthy", "architecture": "Two-Tier..."}

# 3. Sandbox Health Check (From host VM)
curl -f http://127.0.0.1:5050/health
# Expected: {"status": "healthy", "isolation_mode": "container"}

# 4. Master Pentest Regression Verification
cd f_backend
.\venv\Scripts\python.exe -m unittest tests/test_security_regressions.py
# Expected: Ran 8 tests -> OK
```

---

## 9. Rollback & Disaster Recovery Procedures

* **Immediate Rollback Trigger**: If production error rate exceeds 2% or any customer payment fails silently.
* **Frontend Rollback**: In Vercel Dashboard, select previous instant deployment and click **"Promote to Production"** (< 15 seconds).
* **Backend Rollback**: In Railway Dashboard, redeploy previous deployment image hash (< 45 seconds).
* **Database Restoration**: If data corruption occurs, initiate Point-in-Time Recovery (PITR) in Supabase dashboard to restore database state prior to incident timestamp.
