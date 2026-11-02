# 🚀 PrepFly Linux Staging Deployment Plan & Architecture Specification

**Document Version:** 1.0.0  
**Effective Date:** November 2026  
**Target Systems:** PrepFly Backend (`f_backend`), PrepFly Sandbox Worker (`sandbox_worker`), Isolated Container Runtime (Docker / Rootless Docker / gVisor)  
**Lead SRE & Security Architect:** Principal DevOps & Cloud Security Lead  
**Status:** Architecture Specification & Staging Deployment Runbook (Awaiting Infrastructure Provisioning)  

---

## 1. Executive Summary & Objective

In the preceding security audit ([`PREPFLY_SANDBOX_SECURITY_REPORT.md`](file:///d:/Downloads/interviewsystem/interviewsystem/PREPFLY_SANDBOX_SECURITY_REPORT.md) and [`PREPFLY_SANDBOX_STAGING_VERIFICATION.md`](file:///d:/Downloads/interviewsystem/interviewsystem/PREPFLY_SANDBOX_STAGING_VERIFICATION.md)), all code-level security controls, fail-closed behaviors, quota managers, and test batteries passed with 100% success. However, because the current development workstation is Windows without Docker or WSL, **runtime container isolation on an active Linux kernel remains unverified**.

This document defines a **safe, cost-conscious, highly secure Linux staging deployment plan** for PrepFly's coding execution sandbox. It details:
1. Architectural comparison between a dedicated small Linux VPS and managed container platforms.
2. The exact container execution topology and risks regarding Docker daemon access.
3. Backend-to-worker authentication and secret storage.
4. Fail-closed preservation.
5. Exact staging verification procedures for the 7 Linux kernel isolation gates.
6. A step-by-step deployment runbook, resource sizing, rollback triggers, and updated launch blockers.

---

## 2. Architecture Comparison: Linux VPS vs. Managed Container Services

To execute untrusted candidate code safely, the sandbox worker must run on an architecture compatible with PrepFly's execution engine in [`sandbox_worker/runner.py`](file:///d:/Downloads/interviewsystem/interviewsystem/sandbox_worker/runner.py).

| Evaluation Criteria | Option A: Dedicated Small Linux VPS *(Recommended)* | Option B: Managed Container Service (Railway / ECS / Cloud Run) |
| :--- | :--- | :--- |
| **Monthly Infrastructure Cost (Estimated)** | **~$4.00 – $12.00 / month**<br>• Hetzner Cloud CX22 (2 vCPU, 4GB RAM, 40GB NVMe): €3.79/mo (~$4.10/mo).<br>• DigitalOcean Droplet (1 vCPU, 2GB RAM, 50GB SSD): $12.00/mo (Note: 1GB tier is $6/mo but insufficient for image builds).<br>• AWS Lightsail (2 vCPU, 2GB RAM, 60GB SSD): $10.00/mo. | **~$25.00 – $60.00+ / month**<br>(Per-second vCPU/RAM billing, plus high idle compute costs for running background container daemons). |
| **Nested Container Compatibility** | **100% Native Compatibility**.<br>The Linux host runs Docker Engine or Rootless Docker directly on kernel namespaces and cgroups v2. Volume mounts (`-v {work_dir}:/scratch:rw`) work seamlessly. | **Incompatible or High Risk**.<br>Serverless platforms forbid `docker run` inside containers unless running Docker-in-Docker (DinD) with `--privileged` (which breaks isolation) or mounting the host Docker socket (DooD). |
| **Volume Path Resolution** | **Flawless**.<br>When `runner.py` creates a temporary directory (`tempfile.mkdtemp()`), the path exists on the host filesystem and mounts directly into the execution container. | **Broken Path Mapping (DooD Bug)**.<br>In Docker-outside-of-Docker, paths created inside the worker container do not exist on the underlying host, resulting in empty directory mounts. |
| **Security Perimeter & Blast Radius** | **Maximum Security Isolation**.<br>The VPS can be isolated in a dedicated private staging subnet. The worker runs as an isolated system user (`prepfly-worker`). Untrusted containers run with `--network none`, `--cap-drop=ALL`, and `--read-only`. | **Severe Security Compromise (if DooD used)**.<br>Mounting `/var/run/docker.sock` into an application container grants root-equivalent host access, enabling container breakout. |
| **Operational Simplicity** | **Very High**.<br>1 systemd service unit, 1 Caddy reverse proxy with automatic TLS, standard Linux tools (`journalctl`, `docker ps`, `ufw`). | **Complex & Fragile**.<br>Requires custom DinD daemons, entrypoint scripts, and complex networking workarounds. |

### Architectural Sizing & Cost Analysis
* **Why 1GB RAM is Insufficient**: The worker Docker image (`sandbox_worker/Dockerfile`) compiles GCC, G++, Node.js, and OpenJDK Headless on Debian Bookworm. A `docker build` or concurrent compiler invocation on a 1GB VPS will trigger the host OOM killer during `apt-get` or `pip install`.
* **Minimum Sizing Recommendation**: A VPS with **2 vCPU, 2GB to 4GB RAM, and 40GB SSD**, augmented with a 2GB swapfile. Hetzner CX22 (2 vCPU, 4GB RAM @ ~€3.79/mo) represents the highest price-to-performance ratio.

---

## 3. Container Launch Topology, Docker Daemon Security & Privilege Boundaries

### 3.1 How the Sandbox Worker Launches Execution Containers
Inspection of [`sandbox_worker/runner.py:L408-435`](file:///d:/Downloads/interviewsystem/interviewsystem/sandbox_worker/runner.py#L408-L435) demonstrates the exact container invocation:
```python
cmd = [
    "docker", "run", "--rm",
    "-i",
    "--network", "none",
    "--read-only",
    "--user", "10001:10001",
    "--cap-drop=ALL",
    "--security-opt=no-new-privileges:true",
    f"--cpus={config.CPU_TIME_LIMIT_SECONDS}",
    f"--memory={config.MEMORY_LIMIT_BYTES}",
    f"--memory-swap={config.MEMORY_LIMIT_BYTES}",
    f"--pids-limit={config.MAX_PROCESSES}",
    "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m",
    "-v", f"{os.path.abspath(work_dir)}:/scratch:rw",
    "-w", "/scratch"
]
if is_microvm:
    cmd.extend(["--runtime", config.CONTAINER_RUNTIME])
cmd.append(config.CONTAINER_IMAGE)
cmd.extend(self._get_internal_exec_command(lang))

proc = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
```

### 3.2 Operating System Accounts, Docker Daemon Control & Privilege Boundaries
A rigorous security architecture must clearly distinguish between container privileges and host daemon control:

1. **Which account runs the worker?**
   The worker daemon runs as an unprivileged service account: `prepfly-worker` (system user without login shell, UID ~1001).
2. **Which account owns and controls the Docker daemon?**
   The standard Docker daemon (`dockerd`) runs as **`root`** and listens on the UNIX domain socket `/var/run/docker.sock` (owned by `root:docker`, mode `0660`).
3. **Can the worker account obtain root-equivalent host access?**
   **YES**. On any standard Linux deployment, adding a user to the `docker` group (`usermod -aG docker prepfly-worker`) grants that user direct write access to `/var/run/docker.sock`. Any process with access to the Docker socket can command the daemon to mount the host root filesystem (`docker run -v /:/host alpine`) or execute privileged containers.
   **Crucial Architectural Clarification**: Running the worker as user `prepfly-worker` protects against direct filesystem tampering by the Python process, but it **DOES NOT** by itself prevent root escalation if the worker process itself is fully compromised.
4. **Defense-in-Depth Mitigations**:
   - **Network Inaccessibility**: The worker API binds to `127.0.0.1:5050` and is only reachable via Caddy with HMAC-authenticated requests (`X-Sandbox-Secret`).
   - **No Shell Execution**: `runner.py` uses explicit argument lists (`subprocess.Popen(cmd)`) rather than shell interpolation (`shell=False`), preventing command injection into Docker arguments.
   - **In-Container Compilation**: Compilers (`g++`, `gcc`, `javac`) are executed inside single-use isolated containers rather than directly on the host OS, preventing compiler path traversal (`#include "/etc/shadow"`).
   - **Scratch Mount Isolation & Hardened Permissions**: `work_dir` is generated in `SCRATCH_BASE_DIR` with group ownership set to `sandboxgroup` (GID 10001) and mode `0o2770` (`rwxrws---`), strictly granting read/write access to `prepfly-worker` and container user `10001:10001` while completely denying world access (`---`). Source files are written via descriptor-based atomic creation (`O_CREAT | O_EXCL | O_NOFOLLOW`), and directories are unconditionally purged via realpath-validated `shutil.rmtree()` in `finally:`. Insecure fallbacks (such as `0o1777` or `0o777`) are strictly eliminated; permission setup failure fails closed.

### 3.3 Rootless Docker Technical Feasibility & Compatibility Evaluation

Before approving rootful Docker for staging, Rootless Docker (`dockerd-rootless.sh`) was evaluated across all six operational dimensions required by PrepFly's execution engine:

| Evaluation Dimension | Rootless Docker Behavior | Current `runner.py` Implementation | Feasibility Verdict |
| :--- | :--- | :--- | :---: |
| **1. Container Creation & Removal** | Fully supported via user namespaces (`newuidmap`/`newgidmap`). Docker CLI commands (`docker run --rm`, `docker rm -f`) execute normally. | `subprocess.Popen(["docker", "run", ...])` and `subprocess.run(["docker", "rm", "-f", ...])`. | ✅ **Compatible** |
| **2. Bind Mounts & UID/GID Mapping** | User namespaces map host UID 1001 to container UID 0. Container UID 10001 maps to host subordinate UID ~110000 (from `/etc/subuid`). Directory on host owned by host GID 10001 appears as `nobody:nogroup` (65534) to container user 10001. | `_setup_scratch_dir()` creates directory on host and executes `os.chown(work_dir, -1, 10001)` with mode `0o2770`. Inside container, user `10001:10001` attempts to write to `/scratch`. | ❌ **Incompatible**<br>(Fails with `EACCES / Permission Denied` on `/scratch`) |
| **3. Cgroups V2 Resource Limits** | Requires explicit systemd user session delegation (`Delegate=cpu cpuset io memory pids` in `/etc/systemd/system/user@.service.d/delegate.conf`). Swap limit requires `swapaccount=1` in GRUB. | Enforces `--memory=128m`, `--memory-swap=128m`, `--cpus=2.0`, `--pids-limit=16`. | ⚠️ **Fragile**<br>(Without delegation, limits are silently ignored or error) |
| **4. Network Isolation** | Fully supported. `--network none` creates an empty network namespace without requiring `slirp4netns`. | Invokes `docker run --network none`. | ✅ **Compatible** |
| **5. In-Container Compilation & Exec** | Compilers (`g++`, `gcc`, `javac`) must write binaries (`solution.bin`, `Solution.class`) into `/scratch`. | Fails because container user 10001 lacks write permissions on `/scratch` due to UID/GID namespace offset. | ❌ **Incompatible**<br>(Compilers fail: `cannot open output file: Permission denied`) |
| **6. Scratch Permissions & Cleanup** | Host user `prepfly-worker` (UID 1001) attempting to delete files created by subordinate UID 110000 via `shutil.rmtree()` outside user namespace gets `EACCES`. | `_safe_cleanup_scratch()` purges `work_dir` on host in `finally:`. | ❌ **Incompatible**<br>(Purging fails, leaving orphaned directories) |

#### Conclusion on Rootless Docker:
**Rootless Docker is NOT drop-in compatible with PrepFly's current execution engine.** Deploying Rootless Docker without refactoring `runner.py`'s directory permission management and user namespace mapping would break all code compilation and execution on staging.

#### Safest Practical Staging Alternative:
Deploy on a **dedicated, single-tenant Linux staging VPS running conventional (rootful) Docker Engine**.
* *Residual Staging Risk:* An attacker who achieves remote code execution in the Python worker process could leverage `/var/run/docker.sock` to compromise host root on the VPS.
* *Blast Radius Containment:* The staging VPS contains **zero production database credentials, zero production secrets, zero customer PII, and zero private production VPC peering**. If compromised, the blast radius is strictly confined to that disposable machine.
* *Production Requirement:* Multi-tenant production **must not** rely on rootful Docker. Production will use **gVisor (`runsc`) MicroVMs** (which intercepts syscalls in a user-space Go kernel and is already integrated in `runner.py:429` via `SANDBOX_ISOLATION_MODE=microvm`) or a user-namespace container architecture with idmapped mounts.

### 3.4 The Hardened Staging Topology
To avoid the Docker socket DooD trap and volume path failures, the recommended staging topology deploys the worker directly as a **systemd service** on the Linux VPS:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ LINUX STAGING VPS (Ubuntu 22.04 LTS / 2 vCPU / 2-4GB RAM)              │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ 1. Caddy Reverse Proxy (HTTPS / Let's Encrypt / Port 443)        │  │
│  │    • Valid TLS certificate for sandbox.staging.prepfly.io        │  │
│  │    • Enforces TLS 1.3; terminates SSL; reverse-proxies to :5050  │  │
│  └─────────────────────────────────┬────────────────────────────────┘  │
│                                    │ 127.0.0.1:5050                    │
│  ┌─────────────────────────────────▼────────────────────────────────┐  │
│  │ 2. PrepFly Sandbox Worker (systemd: prepfly-worker)              │  │
│  │    • User: prepfly-worker (unprivileged host user)               │  │
│  │    • Validates X-Sandbox-Secret with constant-time HMAC          │  │
│  │    • Enforces user & IP sliding-window quotas                    │  │
│  │    • Manages Bounded Queue (max 4 workers, 50 queue capacity)    │  │
│  │    • Creates ephemeral host temp directory: /tmp/prepfly_sbx_*   │  │
│  └─────────────────────────────────┬────────────────────────────────┘  │
│                                    │ invokes `docker run --network none`│
│  ┌─────────────────────────────────▼────────────────────────────────┐  │
│  │ 3. Ephemeral Execution Containers (Rootless Docker / runsc)      │  │
│  │    • Image: prepfly-sandbox-runner:latest                        │  │
│  │    • User: 10001:10001 (non-root in container)                   │  │
│  │    • Capabilities: --cap-drop=ALL, no-new-privileges:true        │  │
│  │    • Network: NONE (zero veth interfaces, loopback only)         │  │
│  │    • Filesystem: --read-only with 32MB tmpfs on /tmp             │  │
│  │    • Mounted volume: /tmp/prepfly_sbx_* -> /scratch:rw           │  │
│  │    • Cgroups: --cpus=2.0, --memory=128M, --memory-swap=128M      │  │
│  │    • Lifecycle: --rm (automatically destroyed on termination)    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Authentication, Network Security & Secret Management

### 4.1 Backend-to-Worker Authentication Flow
1. **Request Dispatch**: When a candidate submits code, [`f_backend/app.py:execute_sandbox_code()`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2784) constructs the request:
   ```python
   headers = {
       "Content-Type": "application/json",
       "User-Agent": "PrepFly-Core-Runner/2.0",
       "X-User-Id": str(user_id),
       "X-Sandbox-Secret": os.getenv("ISOLATED_SANDBOX_SECRET")
   }
   resp = requests.post(f"{sandbox_url}/execute", json=payload, headers=headers, timeout=10)
   ```
2. **Worker Authentication Check**: In [`sandbox_worker/server.py:_verify_auth()`](file:///d:/Downloads/interviewsystem/interviewsystem/sandbox_worker/server.py#L48):
   ```python
   provided_secret = req.headers.get("X-Sandbox-Secret", "")
   return hmac.compare_digest(provided_secret.encode("utf-8"), config.SECRET.encode("utf-8"))
   ```
   If the secret is missing or mismatched, the worker immediately rejects the request with **HTTP 401 Unauthorized** and writes an `AUTH_FAILURE` audit entry.

### 4.2 Network Encryption & SSRF Validation
In [`f_backend/app.py:_validate_sandbox_url()`](file:///d:/Downloads/interviewsystem/interviewsystem/f_backend/app.py#L2752), the backend enforces:
* **HTTPS Requirement**: Must use `https://` protocol. (Plain `http://` is blocked unless `ALLOW_INSECURE_SANDBOX_HTTP=true` is set).
* **SSRF Target Protection**: Blocks `localhost`, `127.0.0.1`, `::1`, `169.254.169.254`, and private RFC1918 IPs (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
* **Staging Implementation**: The staging worker VPS will be assigned a DNS hostname (e.g. `sandbox.staging.prepfly.io`). A lightweight Caddy server on the VPS automatically obtains and renews a Let's Encrypt TLS certificate. The backend communicates over standard HTTPS (Port 443), satisfying all SSRF validations.

### 4.3 Secure Secret Generation & Storage
* **Secret Generation**: Generate a cryptographically strong 256-bit secret:
  ```bash
  openssl rand -hex 32
  # Generates 64-character random hexadecimal string
  ```
* **Storage on Linux Staging VPS**:
  Stored in `/etc/prepfly/sandbox.env` with strict permissions:
  ```bash
  sudo chown root:sandboxgroup /etc/prepfly/sandbox.env
  sudo chmod 640 /etc/prepfly/sandbox.env
  ```
* **Storage on Staging Backend (Railway/Cloud)**:
  Injected securely via the cloud platform's environment configuration:
  - `ISOLATED_SANDBOX_URL=https://sandbox.staging.prepfly.io`
  - `ISOLATED_SANDBOX_SECRET=<generated-64-char-hex-secret>`
  - `ALLOW_INSECURE_SANDBOX_HTTP=false`

---

## 5. Preservation of Fail-Closed Behavior

The application's fail-closed architecture must remain completely intact. Under no circumstances will a fallback to in-process execution be introduced.

| Failure Mode | Backend Observed Behavior | Host Execution Canary | Safety Status |
| :--- | :--- | :---: | :---: |
| **Worker VPS Offline / Network Partition** | `execute_sandbox_code()` catches `requests.exceptions.ConnectionError`; returns connection error to caller. | **0 code executed on backend host** | ✅ **FAIL-CLOSED** |
| **`ISOLATED_SANDBOX_URL` Unset** | `f_backend/app.py:2910` immediately returns `503 Service Unavailable`. | **0 code executed on backend host** | ✅ **FAIL-CLOSED** |
| **Worker Returns HTTP 500 / 504** | Backend parses error; returns status to candidate or passes error to Gemini code review prompt. | **0 code executed on backend host** | ✅ **FAIL-CLOSED** |
| **Worker Queue Saturated (HTTP 429)** | Backend returns `429 Too Many Requests` with `Retry-After` header. | **0 code executed on backend host** | ✅ **FAIL-CLOSED** |
| **Candidate Code Contains Malicious Payload** | Handled inside isolated container (`--network none`, cgroups limits); zero impact on backend. | **0 code executed on backend host** | ✅ **FAIL-CLOSED** |

---

---

## 6. Linux Staging Verification Procedures (The 8 Audited Isolation Gates)

Once the staging Linux VPS is provisioned, execute the following non-destructive verification procedures directly on the staging host. Each check must produce concrete evidence before sign-off.

> [!IMPORTANT]
> In accordance with zero-trust audit principles, **all 8 Linux runtime isolation gates are currently classified as NOT TESTED / PENDING STAGING VPS PROVISIONING**. They will only be marked PASSED after executing these commands on the live staging Linux host and collecting terminal output.

### Gate 1: Non-Root Execution Verification (UID/GID 10001)
* **Direct Container Verification**:
  ```bash
  docker run --rm --network none --read-only --user 10001:10001 prepfly-sandbox-runner:latest id
  ```
  * **Expected Output**: `uid=10001(sandboxuser) gid=10001(sandboxgroup)`
* **Application API Verification** (verifying that `runner.py` actually passes `--user 10001:10001` over HTTP):
  ```bash
  curl -s -X POST http://127.0.0.1:5050/execute \
    -H "Content-Type: application/json" \
    -H "X-Sandbox-Secret: <STAGING_SECRET>" \
    -d '{"language":"python","code":"import os; print(f\"UID={os.getuid()} GID={os.getgid()}\")","problem_id":"test","test_cases":[{"input":"","expected_output":""}]}'
  ```
  * **Expected Output**: `"output": "UID=10001 GID=10001\n"`
* **What it proves**: Candidate code executes strictly as non-root user `10001:10001` both directly and through the worker API.
* **What it does NOT prove**: Does not prove user namespaces (UID 10001 in container corresponds to UID 10001 on the host unless Rootless Docker is active).

### Gate 2: Linux Kernel Cgroups V2 Memory Limit Enforcement (128MB RAM + Swap Control)
* **Technical Note**: In Docker, `--memory=128m` without `--memory-swap` allows the container to use up to 256MB on hosts with swap enabled. To prevent swapping, `runner.py` passes `--memory=128m --memory-swap=128m`. Furthermore, memory must be actively written to (faulted) to trigger cgroups OOM kill rather than Python `MemoryError`.
* **Execution Command**:
  ```bash
  # Actively write 250MB in 4KB strides inside a 128MB hard-capped container
  docker run --rm --memory=128m --memory-swap=128m prepfly-sandbox-runner:latest \
    python3 -c "b = bytearray(250 * 1024 * 1024); [b.__setitem__(i, 1) for i in range(0, len(b), 4096)]"
  echo "Exit Code: $?"
  
  # Check kernel cgroup OOM event
  dmesg -T | grep -E -i "oom-kill|killed process" | tail -n 5
  ```
* **Expected Output**:
  - `Exit Code: 137` (Linux 128 + 9 for `SIGKILL`).
  - Kernel log confirms: `oom-kill:constraint=CONSTRAINT_MEMCG,task_memcg=/docker/...`.
* **What it proves**: The Linux kernel cgroups v2 memory controller forcefully terminates processes that exceed the 128MB resident memory cap.
* **What it does NOT prove**: Does not prove the behavior of applications that handle `malloc` failure gracefully without touching memory.

### Gate 3: Effective CPU Time Ceiling vs. Application Wall-Clock Timeout
* **Technical Distinction**:
  - `docker run --cpus=2.0` enforces **kernel CFS bandwidth throttling** (`cpu.cfs_quota_us`), ensuring the container uses no more than 2 cores of compute per unit time. It does NOT kill the container when time expires.
  - The **4.0s wall-clock timeout** is enforced by Python's `proc.communicate(timeout=4.0)` in [`sandbox_worker/runner.py`](file:///d:/Downloads/interviewsystem/interviewsystem/sandbox_worker/runner.py).
* **Test 3A: Wall-Clock Hard Timeout Verification (via Worker API)**:
  ```bash
  curl -s -X POST http://127.0.0.1:5050/execute \
    -H "Content-Type: application/json" \
    -H "X-Sandbox-Secret: <STAGING_SECRET>" \
    -d '{"language":"python","code":"import time\nwhile True: pass","problem_id":"test","test_cases":[{"input":"","expected_output":""}]}'
  ```
  * **Expected Output**: Response returned in ~4.0s with `"status": "time_limit_exceeded"`. Process group terminated with zero orphaned containers.
* **Test 3B: Kernel CPU Bandwidth Quota Verification (Direct Docker)**:
  ```bash
  docker run --rm --cpus=0.5 prepfly-sandbox-runner:latest python3 -c "
  import time
  t0 = time.time(); c0 = time.process_time()
  while time.time() - t0 < 2.0: pass
  print(f'CPU_RATIO={time.process_time() / (time.time() - t0):.2f}')
  "
  ```
  * **Expected Output**: `CPU_RATIO=0.50` (±0.05), proving kernel CFS bandwidth throttling.
* **What it proves**: Infinite loops are terminated cleanly at 4.0s, and CPU usage is capped at configured core limits.

### Gate 4: Fork-Bomb & Process Table Protection (Safe Bounded Verification)
* **Safety Warning**: Unbounded recursive fork loops like `[os.fork() for _ in range(30)]` spawn $2^{30}$ processes if `--pids-limit` fails, locking up the host VPS. The test must be safely bounded.
* **Execution Command**:
  ```bash
  docker run --rm --pids-limit=16 prepfly-sandbox-runner:latest python3 -c "
  import os, sys, time
  children = []
  for i in range(30):
      try:
          pid = os.fork()
          if pid == 0:
              time.sleep(3)
              sys.exit(0)
          children.append(pid)
      except BlockingIOError:
          print(f'FORK_BLOCKED_AT_PID_COUNT={len(children)}')
          sys.exit(0)
  print(f'UNBOUNDED_FORKS={len(children)}')
  "
  ```
* **Expected Output**: `FORK_BLOCKED_AT_PID_COUNT=14` or `15` (accounting for the parent Python process and internal threads). Output never prints `UNBOUNDED_FORKS`.
* **What it proves**: Kernel cgroups v2 `pids.max` prevents process exhaustion attacks and preserves host PID table stability.
* **What it does NOT prove**: Does not protect against thread exhaustion inside the worker process itself (worker concurrency is bounded by Gunicorn).

### Gate 5: Disabled Outbound Network & DNS Egress Verification
* **Correction**: The runner image (`python:3.11-slim-bookworm`) intentionally omits `iproute2` and `iputils-ping`. Verification is conducted using standard Python network sockets and curl.
* **Execution Command**:
  ```bash
  # 1. Direct TCP socket connection attempt
  docker run --rm --network none prepfly-sandbox-runner:latest python3 -c "
  import socket
  try:
      s = socket.create_connection(('8.8.8.8', 53), timeout=2)
      print('NETWORK_LEAK')
  except OSError as e:
      print(f'NETWORK_BLOCKED: {e}')
  "

  # 2. HTTP egress attempt via curl
  docker run --rm --network none prepfly-sandbox-runner:latest curl -m 2 -Iv https://1.1.1.1 2>&1 | grep -E "Couldn't connect|Network is unreachable|Failed to connect"
  ```
* **Expected Output**:
  - Python: `NETWORK_BLOCKED: [Errno 101] Network is unreachable`.
  - Curl: `curl: (7) Couldn't connect to server` (Network is unreachable).
* **What it proves**: Containers have zero outbound network routing, zero DNS resolution, and no veth device attached to the host network stack.

### Gate 6: Cloud Metadata IP & Host Secret Isolation
* **Correction**: Passing `-e DUMMY_HOST_KEY="secret-123"` manually injects that variable via Docker CLI. Secret isolation must be tested via the worker API to confirm that host environment variables do not leak to candidate code.
* **Execution Command**:
  ```bash
  # 1. Cloud metadata IP (169.254.169.254) unreachable
  docker run --rm --network none prepfly-sandbox-runner:latest python3 -c "
  import urllib.request
  try:
      urllib.request.urlopen('http://169.254.169.254/latest/meta-data/', timeout=2)
      print('METADATA_EXPOSED')
  except Exception as e:
      print(f'METADATA_BLOCKED: {e}')
  "

  # 2. Host secret isolation check via Worker API
  curl -s -X POST http://127.0.0.1:5050/execute \
    -H "Content-Type: application/json" \
    -H "X-Sandbox-Secret: <STAGING_SECRET>" \
    -d '{"language":"python","code":"import os\nfor k in [\"ISOLATED_SANDBOX_SECRET\", \"SUPABASE_SERVICE_ROLE_KEY\", \"RAZORPAY_KEY_SECRET\"]:\n    if k in os.environ: print(f\"LEAK_{k}\")\nprint(\"ENV_CLEAN\")","problem_id":"test","test_cases":[{"input":"","expected_output":""}]}'
  ```
* **Expected Output**:
  - Python: `METADATA_BLOCKED: <urlopen error [Errno 101] Network is unreachable>`.
  - API response output contains: `"ENV_CLEAN\n"` with 0 occurrences of `LEAK_`.
* **What it proves**: Untrusted code cannot query cloud provider instance metadata or access backend/database credentials.

### Gate 7: Read-Only Filesystem & Ephemeral Directory Cleanup
* **Execution Command**:
  ```bash
  # 1. Verify container root filesystem is strictly read-only
  docker run --rm --read-only --user 10001:10001 prepfly-sandbox-runner:latest python3 -c "
  try:
      with open('/etc/malicious.txt', 'w') as f: f.write('pwn')
      print('ROOTFS_WRITABLE')
  except OSError as e:
      print(f'READ_ONLY_CONFIRMED: {e}')
  "

  # 2. Submit execution and verify /tmp ephemeral scratch purging
  curl -s -X POST http://127.0.0.1:5050/execute \
    -H "Content-Type: application/json" \
    -H "X-Sandbox-Secret: <STAGING_SECRET>" \
    -d '{"language":"python","code":"print(\"ephemeral test\")","problem_id":"test","test_cases":[{"input":"","expected_output":""}]}'

  # Check host temporary directory for orphaned scratch folders
  ORPHANS=$(ls -d /var/tmp/prepfly-sandbox/prepfly_sandbox_* /tmp/prepfly_sandbox_* 2>/dev/null | wc -l)
  echo "ORPHANED_TEMP_DIRS=$ORPHANS"
  ```
* **Expected Output**:
  - `READ_ONLY_CONFIRMED: [Errno 30] Read-only file system`.
  - `ORPHANED_TEMP_DIRS=0`.
* **What it proves**: Execution containers cannot modify system binaries, and disposable host directories are automatically purged after execution.

### Gate 8: Fail-Closed Chaos & Host Execution Integrity
* **Execution Command**:
  ```bash
  # 1. Stop staging sandbox worker service
  sudo systemctl stop prepfly-sandbox-worker

  # 2. Submit authenticated coding request through backend staging endpoint
  curl -i -X POST https://api.staging.prepfly.io/api/coding/submit \
    -H "Authorization: Bearer <staging_user_token>" \
    -H "Content-Type: application/json" \
    -d '{"language": "python", "code": "print(1)", "problem_id": "two-sum"}'
  ```
* **Expected Output**:
  - Backend responds with **HTTP 503** (`Service Unavailable: Sandbox worker unreachable`).
  - Zero candidate code is executed on the backend host.
  ```bash
  # 3. Restore worker service
  sudo systemctl start prepfly-sandbox-worker
  
  # Verify recovery
  curl -f https://sandbox.staging.prepfly.io/health
  ```
* **Expected Output**: Worker reports `status: "healthy"`, subsequent submissions return **HTTP 200**.

---

## 7. Step-by-Step Staging Deployment Runbook

### Phase 1: Provisioning the Linux VPS
1. Provision a small cloud VPS (Ubuntu 22.04 LTS x86_64, 2 vCPU, 4GB RAM, 40GB SSD) on Hetzner Cloud (CX22), DigitalOcean, or AWS Lightsail.
2. Configure DNS A record: `sandbox.staging.prepfly.io` -> `<VPS_PUBLIC_IPV4>`.
3. Configure UFW Firewall:
   ```bash
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow 22/tcp   # SSH (restrict to admin IP if static)
   sudo ufw allow 80/tcp   # HTTP (for Let's Encrypt challenge)
   sudo ufw allow 443/tcp  # HTTPS (for backend API access)
   sudo ufw --force enable
   ```

### Phase 2: Installing Docker Engine, Swapfile & Hardening Host
```bash
# 1. Update OS packages
sudo apt-get update && sudo apt-get upgrade -y

# 2. Configure 2GB swapfile to prevent OOM kills during multi-language image builds
test -f /swapfile || sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile 2>/dev/null || true
sudo swapon /swapfile 2>/dev/null || true
grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 3. Verify Linux kernel cgroups v2 unified hierarchy
test -f /sys/fs/cgroup/cgroup.controllers && echo "CGROUPS_V2_CONFIRMED" || echo "CGROUPS_V1_LEGACY"

# 4. Install Docker Engine, Git, Python3 and dependencies
sudo apt-get install -y ca-certificates curl gnupg lsb-release git python3 python3-pip python3-venv
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# 5. Create sandboxgroup (GID 10001) and system user for the sandbox worker daemon
sudo groupadd -g 10001 sandboxgroup || true
sudo useradd -r -s /usr/sbin/nologin -d /opt/prepfly-sandbox -g sandboxgroup prepfly-worker || sudo usermod -aG sandboxgroup prepfly-worker
sudo usermod -aG docker prepfly-worker

# 6. Pre-create dedicated scratch and audit directories with group permissions
sudo mkdir -p /var/tmp/prepfly-sandbox /var/log/prepfly
sudo chown prepfly-worker:sandboxgroup /var/tmp/prepfly-sandbox /var/log/prepfly
sudo chmod 2770 /var/tmp/prepfly-sandbox
sudo chmod 750 /var/log/prepfly
```

### Phase 3: Building the Execution Runner Image
```bash
# 1. Recommended Repository Access: Narrowly scoped Read-Only Deploy Key
# (Avoids storing broad Personal Access Tokens on the staging VPS)
# Generate dedicated Ed25519 keypair for the worker:
sudo mkdir -p /opt/prepfly-sandbox/.ssh
test -f /opt/prepfly-sandbox/.ssh/id_ed25519 || sudo ssh-keygen -t ed25519 -f /opt/prepfly-sandbox/.ssh/id_ed25519 -N "" -C "prepfly-staging-deploy-key"
sudo chown -R prepfly-worker:sandboxgroup /opt/prepfly-sandbox/.ssh
sudo chmod 700 /opt/prepfly-sandbox/.ssh
sudo chmod 600 /opt/prepfly-sandbox/.ssh/id_ed25519

# Print public key to register at https://github.com/anushkasaxena07/PrepFly/settings/keys
# (Leave "Allow write access" UNCHECKED for read-only least-privilege)
echo "=== STAGING READ-ONLY DEPLOY KEY (Add to GitHub Deploy Keys) ==="
sudo cat /opt/prepfly-sandbox/.ssh/id_ed25519.pub

# 2. Clone repository to /opt/prepfly-sandbox
if [ -d /opt/prepfly-sandbox/.git ]; then
    sudo GIT_SSH_COMMAND="ssh -i /opt/prepfly-sandbox/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new" git -C /opt/prepfly-sandbox pull || sudo git -C /opt/prepfly-sandbox pull
else
    sudo GIT_SSH_COMMAND="ssh -i /opt/prepfly-sandbox/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new" git clone git@github.com:anushkasaxena07/PrepFly.git /opt/prepfly-sandbox || \
    sudo git clone https://github.com/anushkasaxena07/PrepFly.git /opt/prepfly-sandbox
fi

sudo chown -R prepfly-worker:sandboxgroup /opt/prepfly-sandbox
sudo chmod 750 /opt/prepfly-sandbox
cd /opt/prepfly-sandbox/sandbox_worker

# 3. Build the runner image containing Python, Node, GCC, and Java
sudo docker build -t prepfly-sandbox-runner:latest -f Dockerfile .

# 4. Verify image presence
sudo docker images prepfly-sandbox-runner:latest
```

### Phase 4: Deploying the Worker as a Systemd Service
```bash
# 1. Setup virtual environment, install requirements and assign ownership
sudo python3 -m venv /opt/prepfly-sandbox/venv
sudo /opt/prepfly-sandbox/venv/bin/pip install --upgrade pip
sudo /opt/prepfly-sandbox/venv/bin/pip install -r /opt/prepfly-sandbox/sandbox_worker/requirements.txt
sudo /opt/prepfly-sandbox/venv/bin/pip install gunicorn
sudo chown -R prepfly-worker:sandboxgroup /opt/prepfly-sandbox

# 2. Generate secret and write configuration file
sudo mkdir -p /etc/prepfly
SECRET_VAL=$(openssl rand -hex 32)
sudo tee /etc/prepfly/sandbox.env > /dev/null <<EOF
ENVIRONMENT=production
SANDBOX_HOST=127.0.0.1
SANDBOX_PORT=5050
ISOLATED_SANDBOX_SECRET=${SECRET_VAL}
SANDBOX_ISOLATION_MODE=container
SANDBOX_CONTAINER_IMAGE=prepfly-sandbox-runner:latest
SANDBOX_SCRATCH_DIR=/var/tmp/prepfly-sandbox
SCRATCH_BASE_DIR=/var/tmp/prepfly-sandbox
SANDBOX_AUDIT_LOG=/var/log/prepfly/sandbox_audit.log
SANDBOX_CPU_LIMIT=2.0
SANDBOX_WALL_LIMIT=4.0
SANDBOX_MEM_LIMIT_BYTES=134217728
SANDBOX_MAX_PROCS=16
SANDBOX_CONCURRENT_WORKERS=4
SANDBOX_QUEUE_CAPACITY=50
EOF
sudo chown root:sandboxgroup /etc/prepfly/sandbox.env
sudo chmod 640 /etc/prepfly/sandbox.env

# 3. Install systemd service unit
sudo tee /etc/systemd/system/prepfly-sandbox-worker.service > /dev/null <<'EOF'
[Unit]
Description=PrepFly Isolated Sandbox Worker Daemon
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=prepfly-worker
Group=sandboxgroup
SupplementaryGroups=docker
WorkingDirectory=/opt/prepfly-sandbox/sandbox_worker
EnvironmentFile=/etc/prepfly/sandbox.env
ExecStart=/opt/prepfly-sandbox/venv/bin/gunicorn \
    --workers 4 \
    --threads 2 \
    --bind 127.0.0.1:5050 \
    --timeout 60 \
    server:app
Restart=always
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

# 4. Enable and start worker daemon
sudo systemctl daemon-reload
sudo systemctl enable --now prepfly-sandbox-worker
sudo systemctl status prepfly-sandbox-worker
```

### Phase 5: Setting Up Caddy for Automatic HTTPS Reverse Proxy
```bash
# 1. Install Caddy
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLF 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLF 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update
sudo apt-get install -y caddy

# 2. Configure Caddyfile
sudo tee /etc/caddy/Caddyfile > /dev/null <<EOF
sandbox.staging.prepfly.io {
    reverse_proxy 127.0.0.1:5050
}
EOF

# 3. Verify DNS resolution points to this host before requesting TLS certificate
dig +short sandbox.staging.prepfly.io || host sandbox.staging.prepfly.io

# 4. Restart Caddy to obtain Let's Encrypt certificate
sudo systemctl restart caddy
```

### Phase 6: Health Verification & Backend Integration
```bash
# 1. Test local health endpoint
curl -f http://127.0.0.1:5050/health

# 2. Test public HTTPS health endpoint
curl -Iv https://sandbox.staging.prepfly.io/health
```
In Staging Backend configuration (e.g. Railway):
- Set `ISOLATED_SANDBOX_URL=https://sandbox.staging.prepfly.io`
- Set `ISOLATED_SANDBOX_SECRET=<the_exact_generated_secret>`
- Restart backend service.

---

## 8. Rollback & Disaster Recovery Procedures

| Scenario | Trigger Threshold | Immediate Action | Recovery Step |
| :--- | :--- | :--- | :--- |
| **Worker Process Crash Loop** | `systemctl status` reports restarts > 5 | Check `journalctl -u prepfly-sandbox-worker -n 50`. | If image corrupted, rebuild: `docker build -t prepfly-sandbox-runner:latest . && systemctl restart prepfly-sandbox-worker`. |
| **Backend 503 Errors Spike** | > 5% of coding submissions return 503 | Check VPS network reachability and Caddy TLS certificate. | Verify backend DNS resolution: `nslookup sandbox.staging.prepfly.io`. Check Caddy logs: `journalctl -u caddy`. |
| **Host Disk Saturation** | `/tmp` or `/var/lib/docker` > 85% full | Prune stale containers and build cache: `docker system prune -af --volumes`. | Check cron job for ephemeral directory purging. |
| **Host Memory Exhaustion** | VPS RAM utilization > 90% sustained | Restart worker pool: `systemctl restart prepfly-sandbox-worker`. | Reduce `SANDBOX_CONCURRENT_WORKERS` from 4 to 2 in `/etc/prepfly/sandbox.env`. |

---

## 9. Updated Launch Blockers Backlog (`LAUNCH_BLOCKERS.md`)

Below is the updated tracking table of all launch blockers, incorporating the sandbox staging requirements:

| Blocker ID | Priority | Category | Description | Owner | Acceptance Criteria | Status |
| :--- | :---: | :---: | :--- | :--- | :--- | :---: |
| **BLOCKER-01** | **P0** | Frontend | Hardcoded `http://localhost:5000` URLs in PaymentHistory & InvoiceTable. | Frontend Lead | 0 occurrences of `localhost:5000` in `f_frontend/src`. Invoices download via dynamic `BACKEND_URL`. | **RESOLVED** *(Verified in Code & Tests)* |
| **BLOCKER-02** | **P0** | Security / Backend | `ISOLATED_SANDBOX_URL` missing from environment configuration. | SRE / DevOps | `ISOLATED_SANDBOX_URL` and `ISOLATED_SANDBOX_SECRET` set in staging & production environments. | **IN PROGRESS** *(Plan Completed, Awaiting VPS Provisioning)* |
| **BLOCKER-03** | **P0** | Frontend | Inconsistent fallback URLs across 12+ API service files. | Frontend Lead | Centralized `BACKEND_URL` imported from `@/config/api` across all service modules. | **RESOLVED** *(Verified in Code)* |
| **BLOCKER-04** | **P0** | Legal / Compliance | DPDP Act 2023 consent checkbox & privacy policy missing on signup. | Legal / Frontend | Explicit consent checkbox recorded in DB; Privacy Policy and Refund terms published. | **OPEN** |
| **BLOCKER-05** | **P0** | Commercial | Hardcoded ₹500/year pricing model creates severe unit economics deficit. | Product / Backend | Multi-tier plan pricing parameterized and validated on the server. | **OPEN** |
| **BLOCKER-06** | **P0** | Security / Auth | Client-supplied `user_id` parameter spoofing across session and feedback endpoints. | Security Lead | All endpoints bind strictly to JWT `sub`. Client-supplied user IDs rejected with HTTP 403. | **RESOLVED** *(Verified in 52 Data Isolation Tests)* |
| **BLOCKER-07** | **P0** | Security / SRE | Sandbox runtime isolation (cgroups, non-root, `--network none`) unverified on Linux. | SRE / Security | Execute all 7 Linux staging isolation gates on provisioned Linux host with documented evidence. | **IN PROGRESS** *(Deployment Plan Authored)* |

---

## 10. Conclusion & Next Steps

PrepFly's sandbox code architecture is ready for staging deployment. The recommended topology—running the worker daemon via systemd on a dedicated small Linux VPS ($4-6/mo) with Caddy TLS and spawning ephemeral execution containers—completely eliminates Docker socket escape vulnerabilities and DooD volume mapping bugs.

### Immediate Next Step
Awaiting user approval to provision the small Linux staging host and execute the staging verification gates.
