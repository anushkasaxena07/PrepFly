# PrepFly Isolated Sandbox Worker

The PrepFly Sandbox Worker is an isolated, dedicated execution service designed to execute untrusted user-submitted code inside a hardened security boundary.

Untrusted candidate code is **never** executed inside the core Flask web process.

---

## Security Boundaries & Design Guarantees

1. **Non-Root Execution**: Runs under unprivileged user `sandboxuser:sandboxgroup` (UID `10001`).
2. **Read-Only Root Filesystem**: In container deployments, the root filesystem is mounted `read_only: true` with ephemeral disposable `tmpfs` mounts for `/tmp` and `/app/scratch` (`noexec,nosuid`).
3. **No Production Secrets**: The worker environment has zero access to database credentials, Supabase keys, JWT secrets, Razorpay keys, or SMTP credentials. All host environment variables are strictly scrubbed (`build_scrubbed_env`).
4. **Network Isolation**: The worker container operates on an internal bridge with `internal: true` or `network_mode: none`, completely blocking outbound network calls, socket connections, and cloud metadata targets (`169.254.169.254`, `metadata.google.internal`).
5. **Resource Bounds & Process Limits**:
   - **CPU Time Limit**: 2.0s per test case (enforced via `RLIMIT_CPU` / `--cpus`).
   - **Wall-Clock Timeout**: 4.0s hard timeout (enforced with process group `SIGKILL` / `taskkill`).
   - **Compilation Limit**: 10.0s hard limit.
   - **Memory Cap**: 128 MB RAM (enforced via `RLIMIT_AS` / container memory cgroups).
   - **Process Cap**: Max 16 pids per execution (enforced via `RLIMIT_NPROC` / cgroups) to prevent fork bombs.
   - **Output Limit**: 64 KB stdout/stderr buffer truncation to prevent log bloating and memory exhaustion.
   - **Code Size Limit**: 64 KB max payload size.
6. **Queue-Based Concurrency & Throttling**:
   - Fixed pool of worker threads (`MAX_CONCURRENT_WORKERS=4`).
   - Bounded pending queue (`MAX_QUEUE_CAPACITY=50`).
   - Saturated queues fail fast with HTTP 429 Too Many Requests to prevent DoS.
7. **Per-User Quotas & Concurrency Bounds**:
   - Sliding window per-user rate limit (default: 15 submissions / minute, 100 submissions / hour).
   - Maximum 2 concurrent executions per user to prevent noisy neighbor starvation.
   - Unauthenticated guest quota (default: 5 submissions / minute).
8. **Structured Security Audit Logging**:
   - Every execution emits a structured JSON audit record tracking `timestamp`, `event_type`, `job_id`, `client_ip`, `user_id`, `language`, `problem_id`, `status`, `execution_time_ms`, `memory_kb`, `security_flags`, and `isolation_mode`.

---

## API Specification

### `POST /execute`
* **Headers**:
  - `Content-Type: application/json`
  - `X-Sandbox-Secret: <ISOLATED_SANDBOX_SECRET>`
  - `X-User-Id: <user_id>` (optional)
* **Request Body**:
  ```json
  {
    "language": "python",
    "code": "def solve():\n    nums = eval(input())\n    target = int(input())\n    for i in range(len(nums)):\n        for j in range(i + 1, len(nums)):\n            if nums[i] + nums[j] == target:\n                print(f'[{i}, {j}]')\n                return\nsolve()",
    "problem_id": "two-sum",
    "user_id": "user-uuid-12345",
    "test_cases": [
      {
        "input": "[2, 7, 11, 15]\n9",
        "expected_output": "[0, 1]",
        "is_hidden": false
      }
    ]
  }
  ```
* **Response Body (200 OK)**:
  ```json
  {
    "results": [
      {
        "status": "success",
        "passed": true,
        "output": "[0, 1]",
        "expected": "[0, 1]",
        "time_ms": 34.2,
        "mem_kb": 1024.0,
        "is_hidden": false,
        "error": null
      }
    ],
    "isolation_mode": "container"
  }
  ```
* **Response Body (429 Too Many Requests - Quota Exceeded)**:
  ```json
  {
    "error": "Too Many Requests: User quota exceeded (15 runs/minute). Retry in 45s.",
    "retry_after": 45
  }
  ```

### `GET /health`
* **Response**: Reports healthy status, queue load, quota metrics, active isolation mode, and toolchain readiness (`python3`, `node`, `g++`, `gcc`, `java`).

### `GET /metrics`
* **Response**: Reports telemetry metrics: queue depth, total processed, timeouts, active users, and tracking stats.

### `GET /audit/recent?limit=20`
* **Headers**: `X-Sandbox-Secret: <ISOLATED_SANDBOX_SECRET>`
* **Response**: Returns recent structured audit logs for security review and anomaly detection.

---

## Deployment & Isolation Backends

### 1. Docker Compose (Standard Microservice Deployment)
```bash
cd sandbox_worker
docker-compose up -d --build
```

### 2. Disposable Container per Execution
Set `SANDBOX_ISOLATION_MODE=container` in the worker configuration. Each submitted code runs in a single-use disposable container:
```bash
docker run --rm \
  --network none \
  --read-only \
  --user 10001:10001 \
  --cpus 2.0 \
  --memory 128m \
  --pids-limit 16 \
  --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  -v <scratch_dir>:/scratch:rw \
  -w /scratch \
  prepfly-sandbox-runner:latest python3 -I -B solution.py
```

### 3. MicroVM / gVisor Integration
For multi-tenant zero-trust execution, configure Docker to use the **gVisor** (`runsc`) runtime by setting:
```json
{
  "runtimes": {
    "runsc": {
      "path": "/usr/bin/runsc"
    }
  }
}
```
And set `SANDBOX_ISOLATION_MODE=microvm` and `SANDBOX_CONTAINER_RUNTIME=runsc`. The worker will spin up gVisor microVM sandboxes with kernel syscall filtering.

---

## Running the Automated Test Battery
```bash
python -m unittest discover -s sandbox_worker/tests -p "test_*.py"
```
The test battery executes 23 automated tests covering:
- Infinite loops & process wall-clock timeouts.
- Memory bombs & segmentation faults / OOM kills.
- Fork bomb mitigation & process group SIGKILL.
- Secret isolation (verifying no host JWT, Supabase, or Razorpay keys are exposed).
- Filesystem containment (attempted writes to `/etc/passwd`).
- Output buffer flooding truncation.
- Network socket & cloud metadata (`169.254.169.254`) blocking.
- Reflection / dunder attribute sandbox escape attempts.
- Per-user minute, hour, and concurrency quota limits.
- Disposable scratch directory cleanup.
