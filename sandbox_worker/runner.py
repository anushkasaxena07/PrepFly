"""
Core Execution Engine for PrepFly Sandbox Worker.
Implements multi-language compilation and execution under strict resource boundaries.
"""

import os
import sys
import time
import shutil
import subprocess
import tempfile
import signal
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from config import config
from security import sanitize_output, build_scrubbed_env, static_code_check

# Safe filename regex whitelist for source code compilation
SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_\.]+$")


def _safe_write_source(work_dir: str, filename: str, content: str) -> str:
    """
    Safely writes source code into work_dir using descriptor-based creation.
    - Validates filename against strict whitelist (prevents ../ and directory traversal)
    - Enforces O_CREAT | O_EXCL to prevent symlink hijack races (TOCTOU)
    - Sets restrictive file permissions (0660 on POSIX for sandboxgroup, 0600 on Windows)
    - Sets group ownership to GID 10001 (sandboxgroup) on POSIX when supported
    """
    if not filename or not SAFE_FILENAME_RE.match(filename) or ".." in filename or filename.startswith("."):
        raise ValueError(f"Invalid or unsafe source filename: '{filename}'")

    real_work = os.path.realpath(work_dir)
    target_path = os.path.join(real_work, filename)
    real_target = os.path.realpath(target_path)

    # Path traversal check: target must be directly within work_dir
    work_prefix = os.path.join(real_work, "")
    if not real_target.startswith(work_prefix) or os.path.normcase(os.path.dirname(real_target)) != os.path.normcase(real_work):
        raise ValueError(f"Path traversal detected in filename: '{filename}'")

    # Safe descriptor-based open flags
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC

    file_mode = 0o660 if os.name != "nt" else 0o600
    fd = os.open(target_path, flags, file_mode)
    try:
        if hasattr(os, "fchown") and os.name != "nt":
            try:
                os.fchown(fd, -1, 10001)
            except Exception:
                pass
        if hasattr(os, "fchmod") and os.name != "nt":
            try:
                os.fchmod(fd, 0o660)
            except Exception:
                pass
        with open(fd, "w", encoding="utf-8", closefd=True) as f:
            f.write(content)
    except Exception:
        try:
            os.close(fd)
        except Exception:
            pass
        raise

    return target_path


# Try importing resource for POSIX rlimits
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False


def is_docker_available() -> bool:
    """Checks whether the Docker CLI and daemon are operational."""
    if shutil.which("docker") is None:
        return False
    try:
        res = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1.5
        )
        return res.returncode == 0
    except Exception:
        return False


def _make_posix_limits(lang: str):
    """
    Applies POSIX resource limits to the child process before exec.
    Language-aware resource limit enforcement:
      - Mandatory limits (RLIMIT_CPU, RLIMIT_NPROC, RLIMIT_FSIZE, setsid, and RLIMIT_AS for non-JS)
        fail closed and raise RuntimeError if they cannot be enforced.
      - Node.js (V8): 64-bit V8 pointer compression requires a 4GB virtual address reservation
        (PROT_NONE) at engine startup. Setting RLIMIT_AS to 128MB causes immediate ENOMEM in V8.
        For JavaScript, memory is bounded by --max-old-space-size=128 in process mode, and by
        kernel-enforced cgroups (--memory 128m) in container mode.
      - Python, C, C++: RLIMIT_AS = 128MB is strictly enforced.
      - Optional limits (RLIMIT_CORE): Dropping core dumps is attempted; failure is caught as optional.
    """
    if not HAS_RESOURCE:
        return None

    def _apply_limits():
        # 1. Mandatory Session / Process Group creation for clean tree kill
        if hasattr(os, "setsid"):
            try:
                os.setsid()
            except Exception as e:
                raise RuntimeError(f"Security configuration error: failed to establish new session (setsid): {e}")

        # 2. Mandatory CPU time limit (seconds)
        try:
            cpu_sec = int(config.CPU_TIME_LIMIT_SECONDS)
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_sec, cpu_sec + 1))
        except Exception as e:
            raise RuntimeError(f"Security configuration error: failed to enforce mandatory RLIMIT_CPU: {e}")

        # 3. Mandatory Memory limit (Virtual address space bytes)
        # Note: --max-old-space-size=128 limits V8's heap, not total process memory.
        # Production execution of untrusted code must require container isolation and kernel-enforced cgroups.
        # For Python, C, and C++, RLIMIT_AS = 128 MB is strictly enforced.
        if lang not in ("javascript", "js", "node"):
            try:
                mem_bytes = config.MEMORY_LIMIT_BYTES
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            except Exception as e:
                raise RuntimeError(f"Security configuration error: failed to enforce mandatory RLIMIT_AS: {e}")

        # 4. Mandatory Fork-bomb protection (Max processes)
        # Multi-threaded runtimes like Node.js (libuv + V8 compiler threads) and Java require
        # thread headroom on Linux, where RLIMIT_NPROC bounds total threads per UID.
        try:
            nproc_limit = max(config.MAX_PROCESSES * 4, 64) if lang in ("javascript", "js", "node", "java") else config.MAX_PROCESSES
            resource.setrlimit(resource.RLIMIT_NPROC, (nproc_limit, nproc_limit))
        except Exception as e:
            raise RuntimeError(f"Security configuration error: failed to enforce mandatory RLIMIT_NPROC: {e}")

        # 5. Mandatory Output size protection (Max file size created)
        try:
            resource.setrlimit(resource.RLIMIT_FSIZE, (config.MAX_OUTPUT_BYTES * 2, config.MAX_OUTPUT_BYTES * 2))
        except Exception as e:
            raise RuntimeError(f"Security configuration error: failed to enforce mandatory RLIMIT_FSIZE: {e}")

        # 6. Optional platform-dependent limit: Drop core dumps
        if hasattr(resource, "RLIMIT_CORE"):
            try:
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            except Exception:
                # RLIMIT_CORE is optional across varying Unix platforms
                pass

    return _apply_limits


class CodeRunner:
    def __init__(self):
        self.scrubbed_env = build_scrubbed_env()

    def get_isolation_mode(self) -> str:
        """Determines the active isolation backend."""
        is_prod = (
            os.getenv("ENVIRONMENT", "").lower() == "production"
            or os.getenv("FLASK_ENV", "").lower() == "production"
            or getattr(config, "ENVIRONMENT", "").lower() == "production"
        )
        mode = os.getenv("SANDBOX_ISOLATION_MODE", config.ISOLATION_MODE).lower().strip()
        docker_ok = is_docker_available()

        if is_prod:
            if mode == "process":
                raise RuntimeError(
                    "Production security violation: ISOLATION_MODE='process' (weak process-level isolation) "
                    "is strictly forbidden in production. Must use 'container' or 'microvm'."
                )
            if mode == "auto":
                if not docker_ok:
                    raise RuntimeError(
                        "Production security violation: ISOLATION_MODE='auto' cannot find a functional "
                        "container runtime in production. Falling back to process mode is strictly forbidden in production."
                    )
                return "container"
            if mode in ("container", "docker"):
                if not docker_ok:
                    raise RuntimeError(
                        "Production security violation: Container runtime is not operational for ISOLATION_MODE='container'."
                    )
                return "container"
            if mode in ("microvm", "gvisor", "firecracker"):
                if not docker_ok:
                    raise RuntimeError(
                        "Production security violation: MicroVM runtime is not operational for ISOLATION_MODE='microvm'."
                    )
                return "microvm"
            raise RuntimeError(
                f"Production security violation: Invalid ISOLATION_MODE='{mode}'. Must be 'container' or 'microvm'."
            )

        if mode in ("container", "docker"):
            return "container" if docker_ok else "process"
        elif mode in ("microvm", "gvisor", "firecracker"):
            return "microvm" if docker_ok else "process"
        elif mode == "auto":
            return "process"
        return "process"

    def _setup_scratch_dir(self, effective_mode: str) -> str:
        """
        Creates an unpredictable, isolated temporary directory within the configured base.
        Enforces strict group and mode permissions:
          - Container/MicroVM mode: group GID 10001, mode 0770 (owner & sandboxgroup only).
          - Process mode: mode 0700 (owner only).
        Fails closed if the required secure permissions cannot be established.
        """
        base_dir = getattr(config, "SCRATCH_BASE_DIR", None) or tempfile.gettempdir()
        if not os.path.isdir(base_dir):
            try:
                os.makedirs(base_dir, mode=0o770, exist_ok=True)
                if hasattr(os, "chown") and os.name != "nt":
                    try:
                        os.chown(base_dir, -1, 10001)
                        os.chmod(base_dir, 0o2770)
                    except Exception:
                        pass
            except Exception as e:
                raise RuntimeError(f"Failed to create scratch base directory '{base_dir}': {e}")

        real_base = os.path.realpath(base_dir)
        work_dir = tempfile.mkdtemp(prefix="prepfly_sandbox_", dir=real_base)
        real_work = os.path.realpath(work_dir)

        # Path traversal / escape check with boundary separator
        base_prefix = os.path.join(real_base, "")
        if not real_work.startswith(base_prefix):
            shutil.rmtree(work_dir, ignore_errors=True)
            raise RuntimeError(f"Scratch directory '{real_work}' escaped expected base '{real_base}'.")

        is_prod = (
            os.getenv("ENVIRONMENT", "").lower() == "production"
            or os.getenv("FLASK_ENV", "").lower() == "production"
            or getattr(config, "ENVIRONMENT", "").lower() == "production"
        )

        if effective_mode in ("container", "microvm") or is_prod:
            # POSIX host with container execution:
            # Container runs as UID 10001:GID 10001. Host worker runs as prepfly-worker.
            # Require group GID 10001 (sandboxgroup) and mode 02770 (rwxrws--- with setgid).
            # World permissions are strictly 000. Setgid ensures newly created files inherit sandboxgroup.
            if hasattr(os, "chown") and os.name != "nt":
                try:
                    os.chown(work_dir, -1, 10001)
                    os.chmod(work_dir, 0o2770)
                except Exception as e:
                    # FAIL CLOSED: Insecure fallback to world-writable strictly rejected
                    shutil.rmtree(work_dir, ignore_errors=True)
                    raise RuntimeError(
                        f"Security failure: unable to establish secure group ownership (GID 10001) "
                        f"and mode 02770 on '{work_dir}': {e}. Insecure fallback rejected. Failing closed."
                    )
            else:
                try:
                    os.chmod(work_dir, 0o700)
                except Exception:
                    pass
        else:
            # Process mode (local dev/testing): strictly restricted to worker process (0700)
            try:
                if hasattr(os, "chmod"):
                    os.chmod(work_dir, 0o700)
            except Exception:
                pass

        return work_dir

    def _safe_cleanup_scratch(self, work_dir: Optional[str]):
        """Safely purges the temporary disposable directory with symlink and traversal defenses."""
        if not work_dir or not os.path.exists(work_dir):
            return
        try:
            # If the submission directory itself was turned into a symlink, unlink it without following
            if os.path.islink(work_dir):
                try:
                    os.unlink(work_dir)
                except Exception:
                    pass
                return

            real_work = os.path.realpath(work_dir)
            base_dir = getattr(config, "SCRATCH_BASE_DIR", None) or tempfile.gettempdir()
            real_base = os.path.realpath(base_dir)
            real_tmp = os.path.realpath(tempfile.gettempdir())

            # Boundary check: ensure real_work is strictly inside real_base or real_tmp with trailing separator
            base_prefix = os.path.join(real_base, "")
            tmp_prefix = os.path.join(real_tmp, "")
            is_sub_base = real_work.startswith(base_prefix)
            is_sub_tmp = real_work.startswith(tmp_prefix)

            if not (is_sub_base or is_sub_tmp):
                return

            if "prepfly_sandbox_" not in os.path.basename(real_work):
                return

            shutil.rmtree(real_work, ignore_errors=True)
        except Exception:
            pass

    def run_submission(
        self,
        language: str,
        code: str,
        test_cases: List[Dict[str, Any]],
        problem_id: str = "custom"
    ) -> Dict[str, Any]:
        """
        Executes untrusted user code across all provided test cases.
        Guarantees cleanup of temporary files in all execution paths.
        """
        lang = language.lower().strip()
        effective_mode = self.get_isolation_mode()

        # 1. Static pre-check
        is_safe, security_flags = static_code_check(lang, code)
        if not is_safe and config.ENABLE_STATIC_AST_FILTER:
            return {
                "error": f"Code rejected by static security analysis: {', '.join(security_flags)}",
                "security_flags": security_flags,
                "isolation_mode": effective_mode
            }

        # 2. Setup disposable scratch directory with secure permissions (fail-closed)
        work_dir = None
        try:
            work_dir = self._setup_scratch_dir(effective_mode)
        except Exception as e:
            return {
                "error": f"Failed to initialize secure sandbox environment: {str(e)}",
                "isolation_mode": effective_mode,
                "results": [{
                    "status": "system_error",
                    "passed": False,
                    "output": "",
                    "expected": tc.get("expected_output", "") if isinstance(tc, dict) else "",
                    "time_ms": 0.0,
                    "mem_kb": 0.0,
                    "is_hidden": bool(tc.get("is_hidden", False)) if isinstance(tc, dict) else False,
                    "error": str(e)
                } for tc in (test_cases if test_cases else [{}])]
            }

        try:
            # 3. Compile if necessary
            compile_res = self._compile_if_needed(lang, code, work_dir)
            if compile_res is not None:
                # Compilation failed
                return {
                    "results": [{
                        "status": "compilation_error",
                        "passed": False,
                        "output": "",
                        "expected": tc.get("expected_output", ""),
                        "time_ms": 0.0,
                        "mem_kb": 0.0,
                        "is_hidden": bool(tc.get("is_hidden", False)),
                        "error": compile_res
                    } for tc in test_cases],
                    "isolation_mode": effective_mode
                }

            # 4. Execute test cases sequentially
            results = []
            for tc in test_cases:
                tc_input = str(tc.get("input", ""))
                expected_out = str(tc.get("expected_output", "")).strip()
                is_hidden = bool(tc.get("is_hidden", False))

                if effective_mode == "container":
                    exec_result = self._execute_container_case(lang, work_dir, tc_input, is_microvm=False)
                elif effective_mode == "microvm":
                    exec_result = self._execute_container_case(lang, work_dir, tc_input, is_microvm=True)
                else:
                    exec_result = self._execute_single_case(lang, work_dir, tc_input)
                
                # Normalize output for comparison
                clean_output = exec_result["output"].strip()
                passed = (exec_result["status"] == "success" and clean_output == expected_out)

                results.append({
                    "status": exec_result["status"],
                    "passed": passed,
                    "output": clean_output,
                    "expected": expected_out,
                    "time_ms": exec_result["time_ms"],
                    "mem_kb": exec_result["mem_kb"],
                    "is_hidden": is_hidden,
                    "error": exec_result.get("error")
                })

            return {"results": results, "isolation_mode": effective_mode}

        finally:
            if work_dir:
                self._safe_cleanup_scratch(work_dir)

    def _compile_if_needed(self, lang: str, code: str, work_dir: str) -> Optional[str]:
        """Compiles code if needed using safe descriptor-based source writing. Returns error message on failure, or None on success."""
        try:
            if lang in ("python", "python3"):
                _safe_write_source(work_dir, "solution.py", code)
                return None
            elif lang in ("javascript", "js", "node"):
                _safe_write_source(work_dir, "solution.js", code)
                return None
            elif lang in ("cpp", "c++"):
                _safe_write_source(work_dir, "solution.cpp", code)
                cmd = ["g++", "-O2", "-std=c++17", "solution.cpp", "-o", "solution.bin"]
                return self._run_compiler(cmd, work_dir)
            elif lang == "c":
                _safe_write_source(work_dir, "solution.c", code)
                cmd = ["gcc", "-O2", "solution.c", "-o", "solution.bin"]
                return self._run_compiler(cmd, work_dir)
            elif lang == "java":
                _safe_write_source(work_dir, "Solution.java", code)
                cmd = ["javac", "Solution.java"]
                return self._run_compiler(cmd, work_dir)
            else:
                return f"Unsupported language: '{lang}'"
        except Exception as e:
            return f"Source writing error: {str(e)}"

    def _run_compiler(self, cmd: List[str], work_dir: str) -> Optional[str]:
        """Runs compiler with timeout inside isolated container or host with scrubbed environment."""
        try:
            mode = self.get_isolation_mode()
        except Exception:
            mode = "process"

        container_id = f"prepfly_compile_{uuid.uuid4().hex[:12]}"
        if mode in ("container", "microvm"):
            # Compile inside container to avoid host compiler dependencies and isolate includes
            exec_cmd = [
                "docker", "run", "--rm",
                "--name", container_id,
                "--init",
                "-i",
                "--network", "none",
                "--read-only",
                "--user", "10001:10001",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges:true",
                f"--cpus={config.CPU_TIME_LIMIT_SECONDS}",
                f"--memory={config.MEMORY_LIMIT_BYTES * 2}",
                f"--memory-swap={config.MEMORY_LIMIT_BYTES * 2}",
                f"--pids-limit={config.MAX_PROCESSES}",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m",
                "-v", f"{os.path.abspath(work_dir)}:/scratch:rw",
                "-w", "/scratch"
            ]
            if mode == "microvm":
                exec_cmd.extend(["--runtime", config.CONTAINER_RUNTIME])
            exec_cmd.append(config.CONTAINER_IMAGE)
            exec_cmd.extend(cmd)
            run_cwd = None
        else:
            exec_cmd = cmd
            run_cwd = work_dir

        try:
            proc = subprocess.run(
                exec_cmd,
                cwd=run_cwd,
                capture_output=True,
                text=True,
                timeout=config.COMPILATION_TIME_LIMIT_SECONDS,
                env=self.scrubbed_env
            )
            if proc.returncode != 0:
                err_text = proc.stderr or proc.stdout or "Compilation failed"
                return sanitize_output(err_text, 1024)
            return None
        except FileNotFoundError as e:
            return f"Compiler toolchain not found: {e.filename}"
        except subprocess.TimeoutExpired:
            if mode in ("container", "microvm"):
                try:
                    subprocess.run(["docker", "rm", "-f", container_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2.0)
                except Exception:
                    pass
            return f"Compilation timed out after {config.COMPILATION_TIME_LIMIT_SECONDS}s"
        except Exception as e:
            return f"Compilation exception: {str(e)}"
        finally:
            if mode in ("container", "microvm"):
                try:
                    subprocess.run(["docker", "rm", "-f", container_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2.0)
                except Exception:
                    pass

    def _get_exec_command(self, lang: str, work_dir: str) -> List[str]:
        """Returns the command list to execute the compiled or scripted solution."""
        if lang in ("python", "python3"):
            py_bin = sys.executable if os.name == "nt" else "python3"
            return [py_bin, "-I", "-B", os.path.join(work_dir, "solution.py")]
        elif lang in ("javascript", "js", "node"):
            return ["node", "--max-old-space-size=128", os.path.join(work_dir, "solution.js")]
        elif lang in ("cpp", "c++", "c"):
            return [os.path.join(work_dir, "solution.bin")]
        elif lang == "java":
            return ["java", "-Xmx128m", "-cp", work_dir, "Solution"]
        else:
            raise ValueError(f"Unsupported language: {lang}")

    def _execute_single_case(
        self,
        lang: str,
        work_dir: str,
        stdin_input: str
    ) -> Dict[str, Any]:
        """Runs the binary or script for a single test case with strict wall-clock and CPU limits."""
        cmd = self._get_exec_command(lang, work_dir)
        start_time = time.perf_counter()

        preexec = _make_posix_limits(lang) if (HAS_RESOURCE and os.name != "nt") else None
        proc = None
        status = "success"
        error_msg = None
        raw_stdout = ""
        raw_stderr = ""
        mem_kb = 0.0

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=work_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.scrubbed_env,
                preexec_fn=preexec
            )

            try:
                raw_stdout, raw_stderr = proc.communicate(
                    input=stdin_input,
                    timeout=config.WALL_TIME_LIMIT_SECONDS
                )
            except subprocess.TimeoutExpired:
                status = "time_limit_exceeded"
                error_msg = f"Time Limit Exceeded: Execution took longer than {config.WALL_TIME_LIMIT_SECONDS}s"
                self._terminate_process_tree(proc)
                try:
                    raw_stdout, raw_stderr = proc.communicate(timeout=0.5)
                except Exception:
                    pass

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if status != "time_limit_exceeded":
                if proc.returncode != 0:
                    status = "runtime_error"
                    # Decode Unix signals if available
                    sigxcpu = getattr(signal, "SIGXCPU", None)
                    sigsegv = getattr(signal, "SIGSEGV", None)
                    sigbus = getattr(signal, "SIGBUS", None)
                    sig_mem = {c for c in (sigsegv, sigbus) if c is not None}

                    if sigxcpu and proc.returncode == -sigxcpu:
                        status = "time_limit_exceeded"
                        error_msg = "CPU Time Limit Exceeded"
                    elif any(proc.returncode == -code for code in sig_mem):
                        status = "memory_limit_exceeded"
                        error_msg = "Memory Limit Exceeded (Segmentation Fault)"
                    else:
                        error_msg = sanitize_output(raw_stderr or f"Process exited with code {proc.returncode}", 1024)

            # Heuristic memory usage estimation
            mem_kb = min(128.0 * 1024, max(512.0, elapsed_ms * 12.0))

            return {
                "status": status,
                "output": sanitize_output(raw_stdout, config.MAX_OUTPUT_BYTES),
                "time_ms": elapsed_ms,
                "mem_kb": mem_kb,
                "error": error_msg
            }

        except FileNotFoundError as fnf:
            return {
                "status": "runtime_error",
                "output": "",
                "time_ms": 0.0,
                "mem_kb": 0.0,
                "error": f"Execution binary not found: {fnf.filename}"
            }
        except Exception as e:
            return {
                "status": "runtime_error",
                "output": "",
                "time_ms": 0.0,
                "mem_kb": 0.0,
                "error": f"Execution error: {str(e)}"
            }
        finally:
            if proc and proc.poll() is None:
                self._terminate_process_tree(proc)

    def _get_internal_exec_command(self, lang: str) -> List[str]:
        """Returns the in-container command to execute the code."""
        if lang in ("python", "python3"):
            return ["python3", "-I", "-B", "solution.py"]
        elif lang in ("javascript", "js", "node"):
            return ["node", "--max-old-space-size=128", "solution.js"]
        elif lang in ("cpp", "c++", "c"):
            return ["./solution.bin"]
        elif lang == "java":
            return ["java", "-Xmx128m", "-cp", ".", "Solution"]
        else:
            raise ValueError(f"Unsupported language: {lang}")

    def _execute_container_case(
        self,
        lang: str,
        work_dir: str,
        stdin_input: str,
        is_microvm: bool = False
    ) -> Dict[str, Any]:
        """Runs binary or script inside a disposable container or microVM with strict boundaries."""
        container_id = f"prepfly_exec_{uuid.uuid4().hex[:12]}"
        cmd = [
            "docker", "run", "--rm",
            "--name", container_id,
            "--init",
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

        start_time = time.perf_counter()
        proc = None
        status = "success"
        error_msg = None
        raw_stdout = ""
        raw_stderr = ""

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            try:
                raw_stdout, raw_stderr = proc.communicate(
                    input=stdin_input,
                    timeout=config.WALL_TIME_LIMIT_SECONDS
                )
            except subprocess.TimeoutExpired:
                status = "time_limit_exceeded"
                error_msg = f"Time Limit Exceeded: Container execution took longer than {config.WALL_TIME_LIMIT_SECONDS}s"
                try:
                    subprocess.run(["docker", "rm", "-f", container_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2.0)
                except Exception:
                    pass
                self._terminate_process_tree(proc)
                try:
                    raw_stdout, raw_stderr = proc.communicate(timeout=0.5)
                except Exception:
                    pass

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if status != "time_limit_exceeded" and proc.returncode != 0:
                status = "runtime_error"
                if proc.returncode == 137:
                    status = "memory_limit_exceeded"
                    error_msg = "Memory Limit Exceeded (Container OOM Killed)"
                else:
                    error_msg = sanitize_output(raw_stderr or f"Container exited with code {proc.returncode}", 1024)

            mem_kb = min(128.0 * 1024, max(512.0, elapsed_ms * 12.0))
            return {
                "status": status,
                "output": sanitize_output(raw_stdout, config.MAX_OUTPUT_BYTES),
                "time_ms": elapsed_ms,
                "mem_kb": mem_kb,
                "error": error_msg
            }
        except Exception as e:
            return {
                "status": "runtime_error",
                "output": "",
                "time_ms": 0.0,
                "mem_kb": 0.0,
                "error": f"Container runtime error: {str(e)}"
            }
        finally:
            try:
                subprocess.run(["docker", "rm", "-f", container_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2.0)
            except Exception:
                pass
            if proc and proc.poll() is None:
                self._terminate_process_tree(proc)

    def _terminate_process_tree(self, proc: subprocess.Popen):
        """Forcefully kills the entire process tree to prevent orphaned worker processes."""
        try:
            if os.name == "nt":
                # Kill process tree on Windows
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2.0
                )
            else:
                # Kill process group on POSIX
                try:
                    pgid = os.getpgid(proc.pid)
                    os.killpg(pgid, signal.SIGKILL)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=0.5)
            except Exception:
                pass


runner = CodeRunner()

