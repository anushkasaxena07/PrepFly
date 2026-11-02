"""
Security analysis, environment scrubbing, and output sanitization for untrusted code execution.
"""

import ast
import os
import re
from typing import List, Tuple

# ANSI escape sequence filter
ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Dangerous module / call patterns for static pre-checks
DANGEROUS_PYTHON_MODULES = {
    "posix", "nt", "pty", "commands",
    "webbrowser", "antigravity", "subprocess",
    "ctypes", "socket", "urllib", "requests", "http"
}

DANGEROUS_ATTRIBUTES = {
    "__subclasses__", "__bases__", "__mro__", "__globals__", "__builtins__",
    "__code__", "__reduce__", "__reduce_ex__"
}


def sanitize_output(raw_str: str, max_bytes: int = 64 * 1024) -> str:
    """
    Strips ANSI escapes, removes null bytes, normalizes line breaks,
    and truncates output to max_bytes to prevent buffer bloat.
    """
    if not raw_str:
        return ""
    # Strip null bytes and non-printable control characters (except newline, carriage return, tab)
    clean = ANSI_ESCAPE_RE.sub("", raw_str)
    clean = "".join(ch for ch in clean if ch in ("\n", "\r", "\t") or ord(ch) >= 32)
    # Truncate to maximum allowed output size
    if len(clean.encode("utf-8", errors="ignore")) > max_bytes:
        clean = clean[:max_bytes] + "\n... [Output truncated: size limit exceeded]"
    return clean.strip()

def build_scrubbed_env() -> dict:
    """
    Builds a strictly scrubbed environment dictionary for child processes.
    Drops ALL host environment variables, tokens, cloud credentials, and secrets.
    """
    # Safe minimum paths for standard toolchains
    standard_paths = [
        "/usr/local/sbin", "/usr/local/bin",
        "/usr/sbin", "/usr/bin", "/sbin", "/bin"
    ]
    if os.name == "nt":
        # Safe fallback on Windows host for local development
        path_val = os.environ.get("PATH", "C:\\Windows\\system32;C:\\Windows")
    else:
        path_val = ":".join(standard_paths)

    return {
        "PATH": path_val,
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "NODE_OPTIONS": "--max-old-space-size=128"
    }

def static_code_check(language: str, code: str) -> Tuple[bool, List[str]]:
    """
    Lightweight static pre-execution check to flag obvious malicious patterns.
    Returns (is_safe, list_of_security_flags).
    """
    flags = []
    
    if len(code.encode("utf-8")) > 64 * 1024:
        flags.append("CODE_SIZE_EXCEEDED")
        return False, flags

    lang = language.lower().strip()
    if lang in ("python", "python3"):
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                # Flag dangerous attribute access (e.g., __subclasses__, __globals__)
                if isinstance(node, ast.Attribute) and node.attr in DANGEROUS_ATTRIBUTES:
                    flags.append(f"FORBIDDEN_ATTRIBUTE:{node.attr}")
                # Flag dynamic code evaluation
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in ("eval", "exec", "compile", "__import__"):
                        flags.append(f"DYNAMIC_EVAL:{node.func.id}")
                # Flag suspicious imports
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in DANGEROUS_PYTHON_MODULES:
                            flags.append(f"SUSPICIOUS_MODULE:{alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module in DANGEROUS_PYTHON_MODULES:
                        flags.append(f"SUSPICIOUS_MODULE:{node.module}")
        except SyntaxError:
            # Syntax errors will be reported naturally by the interpreter during execution
            pass
        except Exception:
            pass

    # Heuristic checks across all languages
    suspicious_patterns = [
        (r"/etc/shadow", "PASSWD_SHADOW_ACCESS"),
        (r"/etc/passwd", "PASSWD_FILE_ACCESS"),
        (r"169\.254\.169\.254", "METADATA_IP_ATTEMPT"),
        (r"metadata\.google\.internal", "METADATA_HOST_ATTEMPT"),
        (r":(){ :|:& };:", "BASH_FORK_BOMB"),
        (r"socket\s*\.\s*socket", "NETWORK_SOCKET_ATTEMPT"),
        (r"(curl|wget|nc|netcat)\s+[\w\.\-]+", "NETWORK_SHELL_ATTEMPT")
    ]
    for pattern, flag in suspicious_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            flags.append(flag)

    return len(flags) == 0, flags

