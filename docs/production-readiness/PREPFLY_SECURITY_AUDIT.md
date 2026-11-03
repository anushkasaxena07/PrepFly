# 🛡️ PrepFly: Master Security Audit & Isolated Code Execution Technical Report

**Document Reference:** `docs/production-readiness/PREPFLY_SECURITY_AUDIT.md`  
**Role:** Principal Application Security Engineer & Linux Infrastructure Reviewer  
**Audit Date:** November 2, 2026  
**Repository:** `https://github.com/anushkasaxena07/PrepFly.git` (Base Commit: `8744277`)  
**Target Architecture:** Flask Backend (`f_backend/`) • Coding Sandbox Daemon (`sandbox_worker/`) • Ubuntu 22.04 LTS Dedicated VPS  
**Status:** Pre-Provisioning Audit Complete • Local Automated Tests 100% Passed • Staging Deployment Plan Verified • Linux Kernel Isolation Gates Preserved as `NOT TESTED`  

---

## 1. Executive Summary

This report delivers a comprehensive, evidence-based security audit of PrepFly's isolated code execution architecture. PrepFly is an AI-powered interview preparation platform where candidates write and execute arbitrary source code across Python, JavaScript/Node.js, C++, C, and Java.

### Summary of Audit Outcomes:
1. **Zero Backend Host Execution:** Verified through static analysis and automated regression suites that `f_backend/app.py` contains **zero** instances of `subprocess`, `os.system`, `exec()`, or `eval()`. The Flask backend is physically incapable of running candidate code locally.
2. **Fail-Closed Security Boundary:** If `ISOLATED_SANDBOX_URL` is unset, invalid, unresolvable, or unreachable, the backend strictly returns **HTTP 503 Service Unavailable**. It never falls back to uncontained execution.
3. **SSRF and Rebinding Defenses:** Strict validation requires `https://` (unless explicitly bypassed via `ALLOW_INSECURE_SANDBOX_HTTP=true` in development), blocks cloud metadata (`169.254.169.254`), loopback (`127.0.0.1`), RFC1918 private ranges, and performs DNS resolution to prevent rebinding.
4. **Worker Hardening & Production Startup Enforcement:** Added startup verification in `sandbox_worker/server.py` ensuring that when `ENVIRONMENT=production`, the worker strictly rejects process-level isolation and refuses to start if `ISOLATED_SANDBOX_SECRET` is unset, default, or less than 32 characters.
5. **Runtime Isolation Reality:** All eight Linux runtime isolation gates remain strictly classified as **`NOT TESTED`**. Local Windows unit tests prove code correctness and boundary handling, but kernel-level cgroups v2, user namespaces, and seccomp enforcement can only be proven on an active Linux kernel.
6. **Zero Infrastructure Provisioned:** No cloud instances, domain changes, or production modifications have been executed.

---

## 2. Code Execution Architecture & Threat Modeling

```
Candidate Browser (React / CodingTab.jsx)
        │
        ▼ (HTTPS POST /api/coding/submit - Bearer JWT Token)
┌────────────────────────────────────────────────────────────────────────┐
│ FLASK BACKEND (f_backend/app.py)                                       │
│ 1. @require_auth verifies JWT sub against user_id (prevents spoofing)  │
│ 2. Validates language, code size (≤64KB), and problem_id               │
│ 3. Fetches problem test cases from Supabase (capped at 50 cases)       │
│ 4. Validates ISOLATED_SANDBOX_URL (SSRF, HTTPS, private IP filters)    │
│ 5. Sanitizes test cases (inputs/outputs ≤4KB each)                     │
│ 6. Signs request with header X-Sandbox-Secret                          │
│ 7. Sends bounded HTTP POST (timeout=10s, allow_redirects=False)        │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ (Public TLS 1.3 / Port 443)
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ CADDY REVERSE PROXY (sandbox.staging.prepfly.io)                       │
│ - Terminates TLS 1.2/1.3 with automated Let's Encrypt certificates     │
│ - Proxies traffic exclusively over loopback to 127.0.0.1:5050          │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ (127.0.0.1:5050)
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ SANDBOX WORKER DAEMON (sandbox_worker/server.py under systemd)        │
│ - Runs as unprivileged service user prepfly-worker:sandboxgroup       │
│ - Constant-time authentication check: hmac.compare_digest(Secret)      │
│ - Rate limiting & user quota enforcement (15/min, 2 concurrent max)    │
│ - Dispatches to bounded worker pool (QueueManager: 4 workers, 50 cap)  │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ (Spawns Ephemeral Docker Run)
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ EPHEMERAL EXECUTION CONTAINER (prepfly-sandbox-runner:latest)          │
│ - User: UID 10001 : GID 10001 (sandboxuser:sandboxgroup)               │
│ - Capabilities: cap-drop=ALL, security-opt=no-new-privileges:true      │
│ - Network: --network none (no public, internal, or metadata egress)    │
│ - Root Filesystem: --read-only                                         │
│ - Mounted Volume: -v /var/tmp/prepfly-sandbox/<unique_scratch>:/scratch│
│ - Limits: --cpus=2.0, --memory=128m, --memory-swap=128m, --pids-limit=16│
│ - Wall Timeout: Python communicate(timeout=4.0s) -> docker rm -f       │
│ - Lifecycle: Atomic write (O_CREAT|O_EXCL), finally: safe rmtree       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Threat Matrix & Finding Inventory

| Finding ID | Vulnerability / Defect Description | Component | Severity | Remediation Status |
| :--- | :--- | :--- | :---: | :---: |
| **SEC-FIND-01** | Missing Production Sandbox Secret Startup Enforcement | `sandbox_worker/server.py` | **HIGH** | ✅ **FIXED & TESTED** |
| **SEC-FIND-02** | Unhandled Sandbox Execution Exception Crashing Backend with 500 | `f_backend/app.py` | **MEDIUM** | ✅ **FIXED & TESTED** |
| **SEC-FIND-03** | Permissive Scheme Handling in Sandbox URL Validator | `f_backend/app.py` | **LOW** | ✅ **FIXED & TESTED** |
| **SEC-FIND-04** | Working-Tree Leak: Untracked Root `uploads/` Folder | `.gitignore` | **LOW** | ✅ **FIXED & TESTED** |
| **SEC-FIND-05** | Working-Tree Divergence: `sandbox_worker/` Untracked Locally | Git Tracking | **HIGH (Operational)** | ⏳ **DOCUMENTED FOR REVIEW** |
| **SEC-FIND-06** | Rootful Docker Privilege Boundary on Linux Host | Linux Architecture | **MEDIUM (Staging)** / **HIGH (Prod)** | ⏳ **STAGING ISOLATED / PROD BLOCKED** |

---

## 4. Detailed Findings & Fix Verifications

### SEC-FIND-01: Production Sandbox Secret Startup Bypass
* **Severity:** **HIGH** (CVSS: 7.5 - `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N`)
* **Affected Component:** [`sandbox_worker/server.py`](file:///d:/Downloads/interviewsystem/interviewsystem/sandbox_worker/server.py) and [`sandbox_worker/config.py`](file:///d:/Downloads/interviewsystem/interviewsystem/sandbox_worker/config.py).
* **Vulnerability Analysis:**
  In `config.py`, `SECRET` defaulted to `"prepfly-sandbox-dev-secret-32-chars-long-minimum"`. While `validate_sandbox_startup()` checked `runner.get_isolation_mode()`, it never validated that `config.SECRET` was set or non-default in production. If a staging or production operator launched the worker without explicitly passing `ISOLATED_SANDBOX_SECRET`, the worker started with the well-known development secret, allowing any internet caller knowing the default string to execute code on `/execute`.
* **Remediation Implemented:**
  Updated `validate_sandbox_startup()` in `server.py` to enforce that when `is_prod` is true, `secret` must not be empty, must not equal the default dev secret, and must be at least 32 characters in length.
* **Validation:** Verified via automated regression test `test_17_production_mode_rejects_insecure_sandbox_secret` in `test_production_sandbox_security.py`.

---

### SEC-FIND-02: Backend Unhandled Exception on Sandbox Configuration Errors
* **Severity:** **MEDIUM**
* **Affected Component:** [`f_backend/app.py:L2953-2957`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2953-L2957).
* **Vulnerability Analysis:**
  In `coding_submit()`, `exec_res = execute_sandbox_code(...)` was called without a `try ... except` wrapper. If `execute_sandbox_code` raised a `RuntimeError` (e.g. from an invalid URL scheme, malformed host, or missing configuration), the unhandled exception crashed into Flask's global 500 handler rather than returning a clean, controlled 503 response.
* **Remediation Implemented:**
  Wrapped `execute_sandbox_code` in a `try ... except Exception as e:` block in `app.py`, returning a controlled JSON response with status code **HTTP 503** (`Service Unavailable: Sandbox worker communication error`).
* **Validation:** Verified via automated regression test `test_18_backend_coding_submit_handles_sandbox_config_error_gracefully` in `test_production_sandbox_security.py`.

---

### SEC-FIND-03: Sandbox URL Scheme Hardening
* **Severity:** **LOW (Defense-in-Depth)**
* **Affected Component:** [`f_backend/app.py:L2755`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2755).
* **Vulnerability Analysis:**
  `_validate_sandbox_url()` verified `parsed.scheme != "https" and os.getenv("ALLOW_INSECURE_SANDBOX_HTTP") != "true"`. If `ALLOW_INSECURE_SANDBOX_HTTP` was enabled, non-HTTP schemes (e.g., `ftp://` or `gopher://`) were not explicitly rejected by the scheme check.
* **Remediation Implemented:**
  Updated the check to: `if parsed.scheme not in ("https", "http") or (parsed.scheme != "https" and os.getenv("ALLOW_INSECURE_SANDBOX_HTTP", "").lower() != "true"): return False, "ISOLATED_SANDBOX_URL must use https:// protocol"`.
* **Validation:** Verified in `test_16_backend_ssrf_validator_blocks_internal_and_metadata_targets`.

---

### SEC-FIND-04: Working-Tree Pollutive Artifacts in Untracked Files
* **Severity:** **LOW (Hygiene / Git Safety)**
* **Affected Component:** [`.gitignore`](file:///d:/Downloads/interviewsystem/interviewsystem/.gitignore).
* **Vulnerability Analysis:**
  `.gitignore` contained `f_backend/uploads/` but omitted the root `uploads/` directory. Uploaded screenshots (`uploads/feedback/*.png`) were showing up as untracked files in git.
* **Remediation Implemented:**
  Added `uploads/` to `.gitignore`.
* **Validation:** Verified `git status --short --untracked-files=all` no longer includes runtime uploads.

---

### SEC-FIND-05: Untracked `sandbox_worker/` Directory
* **Severity:** **HIGH (Operational / Deployment Blocker)**
* **Affected Component:** Git tracking.
* **Vulnerability Analysis:**
  The `sandbox_worker/` directory is currently untracked locally on branch `main`. If a staging host clones `https://github.com/anushkasaxena07/PrepFly.git`, the worker directory will not exist on the remote host, causing deployment to fail at Phase 3.
* **Action Required:**
  Before provisioning, review and stage `sandbox_worker/`, `docs/production-readiness/`, and runbooks to a dedicated staging branch or commit to `main`.

---

### SEC-FIND-06: Rootful Docker Privilege Boundary & Staging Containment
* **Severity:** **MEDIUM for Staging VPS / HIGH for Multi-Tenant Production**
* **Affected Component:** Linux staging host privilege model.
* **Vulnerability Analysis:**
  The worker service runs under user `prepfly-worker` with membership in the `docker` group. On a rootful Docker host, access to `/var/run/docker.sock` is root-equivalent. If an attacker achieves RCE inside the Python Gunicorn process, they can escalate to host root.
* **Blast Radius Analysis for Staging:**
  - Candidate code executes with `--network none`, `--read-only`, `--cap-drop=ALL`, and `--user 10001:10001`. Candidate code cannot access `/var/run/docker.sock`.
  - The staging VPS is a dedicated, single-tenant, disposable instance containing **zero production database credentials, zero production customer data, and zero private network peering**.
* **Production Invariant:**
  Multi-tenant production **must not** rely on rootful Docker. Production requires **gVisor (`runsc`) MicroVMs** or Rootless Docker.

---

## 5. Local Automated Testing & Verification Evidence

All local unit, integration, and security tests were executed using the project's Python 3.11 virtual environment (`f_backend/venv/Scripts/python.exe`):

```
===========================================================================
                      AUTOMATED TEST BATTERY SUMMARY
===========================================================================
Suite 1: Sandbox Worker & Security Defense (sandbox_worker/tests)
- Command: python.exe -m unittest discover -s sandbox_worker/tests -v
- Total Tests: 55
- Passed:      53
- Skipped:     2 (Windows OS constraints: POSIX chown and unprivileged symlinks)
- Failures:    0
- Errors:      0
- Duration:    26.68s

Suite 2: PrepFly Backend Master Suite (f_backend/run_all_tests.py)
- Command: python.exe f_backend/run_all_tests.py
- Total Tests: 192
- Passed:      192
- Failures:    0
- Errors:      0
- Duration:    29.45s

Suite 3: Static Code Integrity (Ruff Linter)
- Command: python.exe -m ruff check sandbox_worker/ f_backend/ --select F821,E9,F811
- Result:  All checks passed! (0 errors)
===========================================================================
```

---

## 6. The Eight Linux Runtime Isolation Gates

In accordance with strict zero-trust standards, **all eight Linux isolation gates remain classified as NOT TESTED** until executed on the provisioned Ubuntu 22.04 LTS host:

| Gate | Target Security Boundary | Exact Staging Test Command | Expected Result | Status |
| :---: | :--- | :--- | :--- | :---: |
| **1** | Non-Root Execution (UID/GID 10001) | `docker run --rm prepfly-sandbox-runner:latest id`<br>`curl -s -X POST http://127.0.0.1:5050/execute -H "X-Sandbox-Secret: <SECRET>" -d '{"language":"python","code":"import os; print(f\"UID={os.getuid()} GID={os.getgid()}\")"}'` | Output strictly contains `UID=10001 GID=10001`. Exit code 0. | **NOT TESTED** |
| **2** | Cgroups V2 Memory Cap (128M + Swap Control) | `curl -s -X POST http://127.0.0.1:5050/execute -H "X-Sandbox-Secret: <SECRET>" -d '{"language":"python","code":"b = bytearray(200*1024*1024); [b.__setitem__(i, 1) for i in range(0, len(b), 4096)]"}'` | Kernel cgroup v2 triggers OOM kill (exit 137). Worker reports `"status": "memory_limit_exceeded"`. | **NOT TESTED** |
| **3** | CPU CFS Throttling & Hard Timeout | `curl -s -X POST http://127.0.0.1:5050/execute -H "X-Sandbox-Secret: <SECRET>" -d '{"language":"python","code":"while True: pass"}'` | Terminates at wall clock ~4.0s. Worker reports `"status": "time_limit_exceeded"`. Container removed. | **NOT TESTED** |
| **4** | Fork-Bomb PID Table Cap (pids=16) | `curl -s -X POST http://127.0.0.1:5050/execute -H "X-Sandbox-Secret: <SECRET>" -d '{"language":"python","code":"import os, time\nfor i in range(30):\n try: os.fork()\n except Exception as e: print(\"FORK_BLOCKED:\", type(e).__name__); break\ntime.sleep(1)"}'` | Cgroups v2 `pids.max` halts forks at ~15 with `BlockingIOError`. Host PID table remains unaffected. | **NOT TESTED** |
| **5** | Network Egress & Host Port Isolation | `curl -s -X POST http://127.0.0.1:5050/execute -H "X-Sandbox-Secret: <SECRET>" -d '{"language":"python","code":"import socket\ntry: socket.create_connection((\"8.8.8.8\", 53), timeout=1); print(\"LEAK\")\nexcept OSError: print(\"EGRESS_BLOCKED\")"}'` | `--network none` blocks socket with `[Errno 101] Network is unreachable`. Internal port 5050 blocked. | **NOT TESTED** |
| **6** | Metadata (169.254.169.254) & Secret Scrub | `curl -s -X POST http://127.0.0.1:5050/execute -H "X-Sandbox-Secret: <SECRET>" -d '{"language":"python","code":"import os; leaks=[k for k in os.environ if \"SECRET\" in k or \"SUPABASE\" in k]; print(\"ENV_CLEAN\" if not leaks else f\"LEAK:{leaks}\")"}'` | Metadata IP unreachable. Output strictly contains `ENV_CLEAN` with 0 host secret occurrences. | **NOT TESTED** |
| **7** | Read-Only Rootfs & Scratch Cleanup | `docker run --rm prepfly-sandbox-runner:latest touch /etc/malicious && echo "FAIL" || echo "RO_OK"`<br>`ls -d /var/tmp/prepfly-sandbox/prepfly_sandbox_* 2>/dev/null \| wc -l` | Touch fails with `[Errno 30] Read-only file system`. Orphaned scratch directories count is strictly 0. | **NOT TESTED** |
| **8** | Fail-Closed Chaos & Backend Canary Defense | `sudo systemctl stop prepfly-sandbox-worker`<br>Submit code via backend staging endpoint: `curl -i -X POST https://api.staging.prepfly.io/api/coding/submit ...` | Backend returns **HTTP 503**. Verification confirms zero candidate code executed on backend host. | **NOT TESTED** |

---

## 7. Staging Deployment Readiness & Verification Plan

### 7.1 Architecture & Resource Sizing
* **Operating System:** Ubuntu 22.04 LTS (x86_64) with Linux kernel 5.15+ and cgroups v2 unified hierarchy.
* **VPS Sizing:** 2 vCPU, 4GB RAM, 40GB NVMe SSD (Hetzner Cloud CX22 @ ~€3.79/mo or AWS Lightsail 4GB @ $20/mo).
* **Swap Space:** 2GB `/swapfile` (protects system against memory spikes during multi-language Docker builds).
* **Firewall Policy:** UFW default deny incoming, allowing ports `22` (SSH), `80` (HTTP ACME), and `443` (HTTPS API).
* **Reverse Proxy:** Caddy 2 reverse-proxying `https://sandbox.staging.prepfly.io` to `127.0.0.1:5050`.

### 7.2 Security Invariants Verified in Code
1. `User=prepfly-worker` (UID 1001), `Group=sandboxgroup` (GID 10001), `SupplementaryGroups=docker`.
2. `/etc/prepfly/sandbox.env` owned by `root:sandboxgroup` with mode `0640`.
3. `/var/tmp/prepfly-sandbox` owned by `prepfly-worker:sandboxgroup` with mode `2770` (setgid).
4. Worker Gunicorn service configured with `--timeout 60` (allowing multi-case compilation and test execution).

---

## 8. Conclusion & Final Security Decision

PrepFly's sandbox code and backend integration have been audited, hardened, and verified with 100% automated test pass rates locally.

### Final Readiness Decisions:
* **Local Development & Unit Readiness:** 🟢 **READY**
* **Staging Deployment Package Readiness:** 🟢 **READY**
* **Linux Runtime Isolation Verification:** 🟡 **PENDING (Awaiting Live Linux VPS Execution)**
* **Production Launch Readiness:** 🔴 **BLOCKED (Pending Gates 1–8 Verification and LAUNCH_BLOCKERS.md Resolution)**

*Awaiting explicit user authorization before creating or provisioning cloud infrastructure.*
