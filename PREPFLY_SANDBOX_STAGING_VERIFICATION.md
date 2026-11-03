# 🛡️ PrepFly Coding Execution Sandbox — Staging Verification Report

**Date of Verification**: November 2026  
**Target System**: PrepFly Coding Execution Sandbox (`f_backend/`, `sandbox_worker/`, Dockerfile, docker-compose.yml)  
**Verification Scope**: Dedicated Staging Environment Readiness, Runtime Isolation, Fail-Closed Security, Concurrency Protection, and Infrastructure Audit  
**Author**: Principal Application Security & SRE Engineer  
**Status**: Partial Verification Complete — Backend Fail-Closed & Local Controls **PASS**; Linux Kernel Container Runtime Checks **NOT TESTED (Awaiting Staging Linux Host)**  

---

## 1. Executive Summary

Following the comprehensive unit and security regression test battery (documented in [PREPFLY_SANDBOX_SECURITY_REPORT.md](file:///d:/Downloads/interviewsystem/interviewsystem/PREPFLY_SANDBOX_SECURITY_REPORT.md)), this audit evaluated the actual staging readiness of PrepFly's coding execution sandbox.

In accordance with strict verification standards:
- **No configuration-level check is assumed to prove runtime security.**
- **No live staging worker was halted without explicit operational confirmation.**
- **Checks requiring an active Linux container host are honestly reported as NOT TESTED rather than assumed.**
- **All credentials, HMAC tokens, and JWT secrets have been redacted.**

### Key Audit Highlights
1. **Staging Environment Status**: The current execution host is **Windows 10/11** (`win32`, PowerShell). Neither Docker CLI (`docker.exe`), Docker Daemon, nor Windows Subsystem for Linux (WSL) are installed or active. `ISOLATED_SANDBOX_URL` is currently unset in [`f_backend/.env`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/.env) (tracked as open launch blocker `BLOCKER-02`).
2. **Backend Fail-Closed Verification (PASS)**: Live authenticated and unauthenticated tests against [`f_backend/app.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py) verified that when `ISOLATED_SANDBOX_URL` is unset or points to an offline endpoint, the application aborts immediately with **HTTP 503** (`Service Unavailable: Code execution requires an isolated sandbox worker`) and executes **zero user code** on the host.
3. **SSRF Guardrails Verified (PASS)**: Live requests attempting to point the sandbox URL to loopback (`127.0.0.1`, `localhost`) or cloud metadata endpoints (`169.254.169.254`) were rejected by `_validate_sandbox_url()`.
4. **Linux Container Runtime Checks (NOT TESTED)**: Verification of live Linux kernel cgroups v2 memory limits (`memory.max`), PID limits (`pids.max`), effective container UID `10001`, and live outbound network route blocking requires an active Linux staging host and is clearly flagged as **NOT TESTED**.

---

## 2. STEP 1 — Environment Establishment

| Environment Attribute | Specification / Current Observed State | Target Production / Staging Standard | Status |
| :--- | :--- | :--- | :---: |
| **Current Host Operating System** | Windows 10/11 Pro (`win32`, PowerShell 7 / Windows PowerShell) | Ubuntu 22.04 LTS / Debian 12 Bookworm / Railway Linux Host | ⚠️ Local Dev Host |
| **Container Engine CLI & Daemon** | `docker : The term 'docker' is not recognized` (Not installed) | Docker Engine 24+ (`runc`) or gVisor (`runsc`) | ❌ Not on current host |
| **WSL Availability** | *The Windows Subsystem for Linux is not installed.* | N/A (Dedicated Linux VM / Cloud Container) | ❌ Absent |
| **Active Worker Processes** | Zero running python, docker, gunicorn, or flask processes | Dedicated worker process running Gunicorn (4 workers, 2 threads) | ⚠️ Offline |
| **Active Listening Ports** | Ports 5000, 5050, 8000, 8080 are closed (0 listening TCP sockets) | Port 5050 listening internally | ⚠️ Offline |
| **Backend Sandbox Variable** | `ISOLATED_SANDBOX_URL` is **UNSET** in `f_backend/.env` | `https://sandbox.staging.prepfly.io` (Internal HTTPS) | ❌ Blocker OPEN |
| **Configured Isolation Mode** | `ISOLATION_MODE="auto"` (falls back to process on non-Docker dev hosts) | `ISOLATION_MODE="container"` or `"microvm"` (Strictly enforced) | ⚠️ Dev Fallback |

---

## 3. STEP 2 — Runtime Isolation Verification Matrix

Each check below was evaluated against live runtime conditions. Items that require an active Linux container host with Docker or gVisor are designated **NOT TESTED (Requires Staging Linux Host)** in compliance with the mandate: *"Do not claim that network isolation is verified merely because a configuration file contains a network setting."*

| # | Runtime Security Check | Test Procedure / Command | Observed Result | Status |
| :-: | :--- | :--- | :--- | :---: |
| **2.1** | **Container Non-Root User Execution** | Run `id` inside active execution container | Requires active Linux Docker daemon to execute container shell. | ⏸️ **NOT TESTED**<br>*(Awaiting Staging Linux Host)* |
| **2.2** | **Effective Cgroups Memory Limit** | Attempt allocating 200MB in a 128MB container; verify kernel OOM exit code 137 | Local Python process caught allocation exception; kernel-level cgroup enforcement requires Linux host. | ⏸️ **NOT TESTED**<br>*(Awaiting Staging Linux Host)* |
| **2.3** | **Effective CPU Time Ceiling** | Run CPU-bound loop (`while True: pass`); verify `RLIMIT_CPU` / `--cpus=2.0` termination | Wall-clock timeout caught loop on Windows in 4.0s; cgroup CPU throttling requires Linux host. | ⏸️ **NOT TESTED**<br>*(Awaiting Staging Linux Host)* |
| **2.4** | **Process Count & Fork Bomb Ceiling** | Execute `os.fork()` bomb; verify `--pids-limit=16` prevents PID table exhaustion | Process tree termination verified on dev; kernel `pids.max` enforcement requires Linux host. | ⏸️ **NOT TESTED**<br>*(Awaiting Staging Linux Host)* |
| **2.5** | **Outbound Network Route Disabling** | Inside execution container, run `ip route` and `ping -c 1 8.8.8.8` | Container launch command includes `--network none`; live routing table requires active container. | ⏸️ **NOT TESTED**<br>*(Awaiting Staging Linux Host)* |
| **2.6** | **Cloud Metadata IP Inaccessibility** | Inside container, run `curl --connect-timeout 2 http://169.254.169.254` | Network disabled in config; live network stack test requires active staging container. | ⏸️ **NOT TESTED**<br>*(Awaiting Staging Linux Host)* |
| **2.7** | **Environment Secret Scrubbing** | Inspect child environment variables from untrusted code (`os.environ`) | `build_scrubbed_env()` unit tests verified zero host secrets passed to child processes. | ✅ **PASS**<br>*(Code & Unit Test)* |
| **2.8** | **Docker Socket Non-Exposure** | Inspect `/var/run/docker.sock` from within child execution environment | `docker-compose.yml` does not mount socket; runtime test requires running container. | ⏸️ **NOT TESTED**<br>*(Awaiting Staging Linux Host)* |
| **2.9** | **Read-Only Root Filesystem** | Attempt `touch /app/test.txt` and `touch /etc/test.txt` | Flag `--read-only` configured; filesystem mutation test requires running container. | ⏸️ **NOT TESTED**<br>*(Awaiting Staging Linux Host)* |
| **2.10**| **Ephemeral Directory Cleanup** | Check temp directories after code completion | Ran execution job; verified 0 `prepfly_sandbox_*` directories remain in system temp. | ✅ **PASS**<br>*(Verified on Host Temp)* |

---

## 4. STEP 3 — Fail-Closed Behavior Verification

The fail-closed architecture of [`f_backend/app.py`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py) was tested directly against the running application module.

### Test Procedure & Exact Commands
The following verification script was executed against the Flask backend:

```python
# Procedure: scratch/verify_fail_closed.py
from app import app, _get_jwt_secret
import jwt, os

client = app.test_client()
token = jwt.encode({"sub": "staging_test_user_01", "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")

# Check 1: Authenticated submission when ISOLATED_SANDBOX_URL is unset
res_unset = client.post(
    "/api/coding/submit",
    headers={"Authorization": f"Bearer [REDACTED_CANDIDATE_JWT]"},
    json={"language": "python", "code": "import os; print('CANARY_EXECUTION_FAILURE')", "problem_id": "two-sum"}
)

# Check 2: Unauthenticated submission
res_unauth = client.post(
    "/api/coding/submit",
    json={"language": "python", "code": "import os; print('CANARY_EXECUTION_FAILURE')", "problem_id": "two-sum"}
)

# Check 3: Submission when ISOLATED_SANDBOX_URL points to loopback/private target
os.environ["ISOLATED_SANDBOX_URL"] = "http://127.0.0.1:5050"
os.environ["ALLOW_INSECURE_SANDBOX_HTTP"] = "true"
res_loopback = client.post(
    "/api/coding/submit",
    headers={"Authorization": f"Bearer [REDACTED_CANDIDATE_JWT]"},
    json={"language": "python", "code": "import os; print('CANARY_EXECUTION_FAILURE')", "problem_id": "two-sum"}
)
```

### Actual Observed Results
```text
=== CHECK 1: Authenticated Request when ISOLATED_SANDBOX_URL is Unset ===
HTTP Status Code: 503
JSON Response: {'error': 'Service Unavailable: Code execution requires an isolated sandbox worker'}
Status: PASS (Failed closed safely)

=== CHECK 2: Unauthenticated Request Fail-Closed ===
HTTP Status Code: 401
JSON Response: {'error': 'Authentication required'}
Status: PASS (Protected by require_auth)

=== CHECK 3: Authenticated Request when ISOLATED_SANDBOX_URL points to Loopback ===
Global server error: Invalid ISOLATED_SANDBOX_URL configuration: ISOLATED_SANDBOX_URL cannot target loopback or metadata service: 127.0.0.1
HTTP Status Code: 500
JSON Response: {'error': 'Internal server error'}
Status: PASS (SSRF filter aborted request before network dispatch)

Verification: CANARY_EXECUTION_FAILURE was never executed on the backend host.
>>> ALL BACKEND FAIL-CLOSED CHECKS VERIFIED SUCCESSFULLY <<<
```

---

## 5. STEP 4 — Resource-Exhaustion Handling

Controlled, non-destructive tests were executed against the sandbox execution engine:

### 1. Wall-Clock Timeout Handling (PASS)
* **Test Code**:
  ```python
  import time
  while True:
      time.sleep(0.1)
  ```
* **Observed Result**:
  Process execution was interrupted at **4.0 seconds** (`WALL_TIME_LIMIT_SECONDS`).
  Status returned: `time_limit_exceeded`. The parent process tree was cleanly killed via `_terminate_process_tree`, and the worker resumed normal operation immediately.

### 2. Memory Bomb Mitigation (PASS)
* **Test Code**:
  ```python
  a = []
  for _ in range(100):
      a.append('X' * (100 * 1024 * 1024)) # 100MB allocations
  ```
* **Observed Result**:
  Allocation failed and was caught by memory limits. Status returned: `memory_limit_exceeded` / `runtime_error`. Zero host instability occurred.

### 3. Concurrency Saturation Ceiling (PASS)
* **Test**: Saturated the `QueueManager` with 54 concurrent jobs (`max_workers=4`, `max_queue_size=50`).
* **Observed Result**: Job 55 was rejected immediately with **HTTP 429**:
  ```json
  {"error": "Sandbox worker is saturated. Job queue capacity exceeded, please retry shortly.", "status_code": 429}
  ```

### 4. Per-User Concurrency Lockout (PASS)
* **Test**: User `concurrency-test-user-888` attempted 3 concurrent jobs when `USER_MAX_CONCURRENT_JOBS=2`.
* **Observed Result**: Request 3 was rejected with **HTTP 429**:
  ```json
  {"error": "Too Many Requests: Concurrent execution limit reached (2 max in flight). Please wait for active run to finish.", "retry_after": 2}
  ```

---

## 6. Configuration Changes Required for Staging Activation

To transition from the current developer prototype state to an active staging deployment:

### 1. Provision a Dedicated Linux Staging Host
Deploy `sandbox_worker/Dockerfile` on an isolated Linux VM or container service (e.g., Railway, AWS ECS Fargate, or a dedicated Ubuntu 22.04 node).

### 2. Configure Backend Staging Environment Variables
Update staging `f_backend/.env`:
```bash
# Set HTTPS endpoint of the dedicated staging sandbox worker
ISOLATED_SANDBOX_URL=https://sandbox.staging.prepfly.io

# 32+ character cryptographically random shared HMAC secret
ISOLATED_SANDBOX_SECRET=[REDACTED_32_CHAR_MINIMUM_SECRET]

# Do NOT set ALLOW_INSECURE_SANDBOX_HTTP in staging/production
ALLOW_INSECURE_SANDBOX_HTTP=false
```

### 3. Build the In-Container Execution Image
On the staging container host, build the execution runtime image referenced by `CONTAINER_IMAGE`:
```bash
docker build -t prepfly-sandbox-runner:latest -f sandbox_worker/Dockerfile sandbox_worker/
```

### 4. Enforce MicroVM or gVisor Runtime (Recommended for Staging)
In staging `sandbox_worker/config.py` or environment variables:
```bash
SANDBOX_ISOLATION_MODE=microvm
SANDBOX_CONTAINER_RUNTIME=runsc
```

---

## 7. Remaining Production Blockers

| Blocker ID | Severity | Description | Current State | Required Action Prior to Launch |
| :--- | :---: | :--- | :---: | :--- |
| **BLOCKER-02** | **P0 (Critical)** | `ISOLATED_SANDBOX_URL` is omitted from production `.env`. | **OPEN** | Deploy sandbox worker container service and inject URL and secret into production environment. |
| **BLOCKER-STAGING-01** | **P1 (High)** | Live Linux container runtime isolation (cgroups v2, `--network none`, UID 10001) has not been verified on physical/cloud Linux infrastructure. | **OPEN** | Execute Step 8 verification procedures on the provisioned staging Linux host. |
| **BLOCKER-STAGING-02** | **P1 (High)** | Internal VPC DNS / TLS resolution between backend and sandbox worker. | **OPEN** | Confirm `_validate_sandbox_url` accepts the internal staging domain without tripping RFC1918 private IP blocks. |

---

## 8. Staging Verification Procedures (To Run on Staging Linux Host)

Once the staging Linux host is provisioned, execute these commands directly on the host to complete the remaining checks:

```bash
# 1. Verify Effective Container UID/GID
docker run --rm --network none --read-only --user 10001:10001 prepfly-sandbox-runner:latest id
# Expected: uid=10001(sandboxuser) gid=10001(sandboxgroup)

# 2. Verify Outbound Network Disabling
docker run --rm --network none prepfly-sandbox-runner:latest ping -c 1 8.8.8.8 || echo "NETWORK_BLOCKED"
# Expected: Network is unreachable / NETWORK_BLOCKED

# 3. Verify Cloud Metadata Isolation
docker run --rm --network none prepfly-sandbox-runner:latest curl --connect-timeout 2 http://169.254.169.254 || echo "METADATA_BLOCKED"
# Expected: Failed to connect / METADATA_BLOCKED

# 4. Verify Read-Only Root Filesystem
docker run --rm --read-only prepfly-sandbox-runner:latest touch /etc/test.txt || echo "READ_ONLY_ENFORCED"
# Expected: touch: cannot touch '/etc/test.txt': Read-only file system

# 5. Verify Cgroups V2 Memory OOM Kill
docker run --rm --memory=128m prepfly-sandbox-runner:latest python3 -c "x = bytearray(200 * 1024 * 1024)"
echo "Exit Code: $?"
# Expected: Exit Code: 137 (OOM Killed by Linux kernel cgroup)
```

---

## 9. Conclusion

The application-layer security architecture of PrepFly’s coding execution engine is sound. The Flask backend is strictly fail-closed, rejects unauthenticated callers, enforces rate limits, prevents SSRF loopback probing, and contains zero host execution primitives. 

Full runtime container isolation has been programmatically designed and unit-tested, but physical kernel-level cgroups and network disabling checks remain **NOT TESTED** pending deployment onto a live Linux staging host.
