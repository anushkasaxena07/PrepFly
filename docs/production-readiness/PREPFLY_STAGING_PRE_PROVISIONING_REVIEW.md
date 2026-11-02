# 🛡️ PrepFly: Staging Pre-Provisioning Engineering & Security Review

**Document Reference:** `docs/production-readiness/PREPFLY_STAGING_PRE_PROVISIONING_REVIEW.md`  
**Role:** Senior Application Security Engineer, Python Backend Engineer, DevSecOps Engineer & Linux Infrastructure Engineer  
**Date:** November 2, 2026  
**Repository:** `https://github.com/anushkasaxena07/PrepFly.git` (Base Commit: `8744277`)  
**Target Environment:** Dedicated Ubuntu 22.04 LTS (x86_64) Staging Host • Gunicorn • Docker Daemon • Caddy Reverse Proxy  
**Current Status:** Pre-Provisioning Validation Complete • Zero Cloud Resources Created • All 8 Linux Isolation Gates Preserved as `NOT TESTED`  

---

## 1. Scope & System Overview

This pre-provisioning review evaluates the technical implementation, security controls, code execution boundaries, and operational runbooks for PrepFly's coding sandbox execution service.

### Evaluated Components:
* **Backend Services:** [`f_backend/app.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py) (`coding_submit`, `execute_sandbox_code`, `_validate_sandbox_url`), authentication middleware (`@require_auth`), and test suites.
* **Sandbox Worker Daemon:** [`sandbox_worker/server.py`](file:///d:/Downloads/interviewsystem/interviewsystem/sandbox_worker/server.py), [`sandbox_worker/runner.py`](file:///d:/Downloads/interviewsystem/interviewsystem/sandbox_worker/runner.py), [`sandbox_worker/config.py`](file:///d:/Downloads/interviewsystem/interviewsystem/sandbox_worker/config.py), and [`sandbox_worker/Dockerfile`](file:///d:/Downloads/interviewsystem/interviewsystem/sandbox_worker/Dockerfile).
* **Staging Infrastructure Manifests:** [`PREPFLY_LINUX_STAGING_DEPLOYMENT_PLAN.md`](file:///d:/Downloads/interviewsystem/interviewsystem/PREPFLY_LINUX_STAGING_DEPLOYMENT_PLAN.md), [`PREPFLY_STAGING_RUNBOOK_VALIDATION.md`](file:///d:/Downloads/interviewsystem/interviewsystem/PREPFLY_STAGING_RUNBOOK_VALIDATION.md), and systemd service unit configurations.
* **Launch Readiness Backlog:** [`docs/production-readiness/LAUNCH_BLOCKERS.md`](file:///d:/Downloads/interviewsystem/interviewsystem/docs/production-readiness/LAUNCH_BLOCKERS.md).

---

## 2. Repository Baseline & Git State

* **Active Git Branch:** `main`
* **Base Commit Hash:** `8744277` (`fix: adjust speech engine metrics to penalize filler word ratio and short response completeness accurately`)
* **Remote:** `origin https://github.com/anushkasaxena07/PrepFly.git`
* **Development Host OS:** Windows 10/11 x86_64
* **Python Version:** 3.11.5 (`f_backend/venv/Scripts/python.exe`)
* **Docker CLI Availability:** Not installed on development host (`CommandNotFoundException`). All container tests are mocked or skipped on Windows.
* **Working Tree State:**
  - Untracked directories: [`sandbox_worker/`](file:///d:/Downloads/interviewsystem/interviewsystem/sandbox_worker), [`docs/production-readiness/`](file:///d:/Downloads/interviewsystem/interviewsystem/docs/production-readiness).
  - Modified tracked files: [`.gitignore`](file:///d:/Downloads/interviewsystem/interviewsystem/.gitignore), [`f_backend/app.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py).
  - Ignored runtime files: `uploads/`, `venv/`, `.env`.
  - **Commit / Push Status:** Zero commits and zero pushes were made. Existing working tree preserved.

---

## 3. Confirmed Findings & Severity Matrix

| Finding ID | Title | Severity | Affected Component | Status |
| :--- | :--- | :---: | :--- | :---: |
| **SEC-01** | Production Startup Allowed Default Dev Secret | **HIGH** | `sandbox_worker/server.py` | ✅ **Fixed & Verified** |
| **SEC-02** | Untracked `sandbox_worker/` Directory in Git | **HIGH (Operational)** | Repository Tracking | ⏳ **Awaiting Git Commit Authorization** |
| **SEC-03** | Unhandled Sandbox Error Triggered HTTP 500 | **MEDIUM** | `f_backend/app.py` | ✅ **Fixed & Verified** |
| **SEC-04** | Inconsistent Scratch Directory Environment Variable | **MEDIUM** | `sandbox_worker/config.py` & Runbook | ✅ **Fixed & Verified** |
| **SEC-05** | Rootful Docker Privilege Boundary on Linux Host | **MEDIUM (Staging)** / **HIGH (Prod)** | Deployment Architecture | ⚠️ **Acceptable for Isolated Staging; Blocked for Prod** |
| **SEC-06** | Permissive Scheme Check in URL Validator | **LOW** | `f_backend/app.py` | ✅ **Fixed & Verified** |
| **SEC-07** | Local Runtime Uploads Polluting Untracked Files | **LOW** | `.gitignore` | ✅ **Fixed & Verified** |

---

## 4. Remediation Implemented

1. **Production Secret Enforcement:**
   - *File:* [`sandbox_worker/server.py:L39-48`](file:///d:/Downloads/interviewsystem/interviewsystem/sandbox_worker/server.py#L39-L48)
   - *Fix:* Enforces that when `ENVIRONMENT=production`, the service refuses to start if `ISOLATED_SANDBOX_SECRET` is unset, default, or less than 32 characters.
   - *Validation:* Verified by `test_17_production_mode_rejects_insecure_sandbox_secret` in `test_production_sandbox_security.py`.
2. **Backend Fail-Closed Handling:**
   - *File:* [`f_backend/app.py:L2953-2957`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2953-L2957)
   - *Fix:* Wrapped `execute_sandbox_code` in a `try ... except` block returning **HTTP 503** on configuration or connection exceptions.
   - *Validation:* Verified by `test_18_backend_coding_submit_handles_sandbox_config_error_gracefully`.
3. **Environment Variable Harmonization:**
   - *File:* [`sandbox_worker/config.py:L54`](file:///d:/Downloads/interviewsystem/interviewsystem/sandbox_worker/config.py#L54) and [`PREPFLY_LINUX_STAGING_DEPLOYMENT_PLAN.md:L510`](file:///d:/Downloads/interviewsystem/interviewsystem/PREPFLY_LINUX_STAGING_DEPLOYMENT_PLAN.md#L510)
   - *Fix:* Supported both `SANDBOX_SCRATCH_DIR` and `SCRATCH_BASE_DIR` in `config.py` and defined both in the `sandbox.env` template.
4. **URL Scheme Restriction:**
   - *File:* [`f_backend/app.py:L2752`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2752)
   - *Fix:* Explicitly restricted URL schemes to `https` (or `http` only when `ALLOW_INSECURE_SANDBOX_HTTP=true`).
5. **Git Upload Hygiene:**
   - *File:* [`.gitignore:L34`](file:///d:/Downloads/interviewsystem/interviewsystem/.gitignore#L34)
   - *Fix:* Added `uploads/` to `.gitignore`.

---

## 5. Automated Tests Executed & Actual Results

| Test Battery | Command Executed | Tests | Passed | Skipped | Failed | Duration | Result |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Sandbox Worker Unit & Defense** | `python.exe -m unittest discover -s sandbox_worker/tests -v` | **55** | **53** | **2\*** | **0** | 26.68s | 🟢 **PASS** |
| **Backend Master Test Suite** | `python.exe f_backend/run_all_tests.py` | **192** | **192** | **0** | **0** | 29.45s | 🟢 **PASS** |
| **Static Code Integrity (Ruff)** | `python.exe -m ruff check sandbox_worker/ f_backend/ docs/ --select F821,E9,F811` | — | All Clean | — | **0** | 0.85s | 🟢 **PASS** |

*\*Note: 2 tests cleanly skipped due to Windows OS constraints (`test_05` POSIX chown and `test_08` symlinks without elevation).*

---

## 6. The Eight Linux Isolation Gates (Status: NOT TESTED)

All eight gates remain strictly **NOT TESTED** pending live staging execution:

| Gate | Target Security Boundary | Staging Verification Command | Status |
| :---: | :--- | :--- | :---: |
| **1** | Non-Root Execution (UID/GID 10001) | `docker run --rm prepfly-sandbox-runner:latest id` + API verification | **NOT TESTED** |
| **2** | Cgroups V2 Memory Cap (128M + Swap 128M) | 200MB active byte dirtying script triggering exit code 137 / OOM kill | **NOT TESTED** |
| **3** | CPU CFS Throttling & Hard 4.0s Wall Timeout | Infinite loop script terminating at wall clock 4.0s (`time_limit_exceeded`) | **NOT TESTED** |
| **4** | Fork-Bomb PID Table Cap (pids=16) | Bounded 30-fork loop stopped at ~15 child processes with `BlockingIOError` | **NOT TESTED** |
| **5** | Network Egress & Host Port Isolation | Socket connection to `8.8.8.8:53` and host port `5050` returning unreachable | **NOT TESTED** |
| **6** | Metadata (169.254.169.254) & Secret Scrub | Metadata curl failure + inspecting `os.environ` for zero host secrets | **NOT TESTED** |
| **7** | Read-Only Rootfs & Scratch Cleanup | Write attempt to `/etc/malicious` returning Errno 30 + 0 orphaned folders | **NOT TESTED** |
| **8** | Fail-Closed Chaos & Host Canary Defense | Stopping worker daemon -> backend returns 503 + zero canary execution | **NOT TESTED** |

---

## 7. Residual Risks & Staging Privilege Boundary

1. **Rootful Docker on Staging:**  
   The worker user `prepfly-worker` belongs to the `docker` group. While candidate code executes in a tightly bounded container (`--network none`, `--read-only`, `--cap-drop=ALL`, `--user 10001:10001`), access to `/var/run/docker.sock` allows any process that achieves RCE in the worker daemon to obtain host root.  
   *Staging Containment:* This risk is acceptable for an isolated, single-tenant, disposable staging VPS with **zero production credentials, zero production customer data, and zero internal VPC routing**.
2. **Production Multi-Tenancy Boundary:**  
   Multi-tenant production **must not** rely on rootful Docker. Production requires **gVisor (`runsc`) MicroVMs** or Rootless Docker.

---

## 8. Deployment Prerequisites & Recommended Next Actions

1. **Step 1 (User Action):** Review and commit untracked files (`sandbox_worker/`, `docs/production-readiness/`) to a staging branch (e.g., `staging/sandbox-worker`) and push to GitHub.
2. **Step 2 (User Action):** Provision 1x Ubuntu 22.04 LTS VPS (2 vCPU, 4GB RAM) on Hetzner Cloud (CX22 @ ~€3.79/mo) or AWS Lightsail ($20/mo).
3. **Step 3 (User Action):** Configure DNS A record pointing `sandbox.staging.prepfly.io` to the VPS IPv4 address.
4. **Step 4:** Execute Phases 1–5 of [`PREPFLY_LINUX_STAGING_DEPLOYMENT_PLAN.md`](file:///d:/Downloads/interviewsystem/interviewsystem/PREPFLY_LINUX_STAGING_DEPLOYMENT_PLAN.md).
5. **Step 5:** Execute all 8 Linux Isolation Gates and attach terminal evidence to [`PREPFLY_STAGING_RUNBOOK_VALIDATION.md`](file:///d:/Downloads/interviewsystem/interviewsystem/PREPFLY_STAGING_RUNBOOK_VALIDATION.md).

*Stopped and awaiting user explicit authorization before any cloud infrastructure is provisioned.*
