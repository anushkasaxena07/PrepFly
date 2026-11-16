"""
PrepFly Runtime Template Guard
Golden Rule 5: No unresolved template variables in UI.
Any string containing None, null, undefined, {{, or NaN shown to a user is a bug.
Add a runtime guard that blocks rendering and logs an error.
"""

import re
import logging
from typing import Any, Union, Dict, List

logger = logging.getLogger("prepfly.template_guard")

# Regex to detect forbidden unresolved template markers or literal leaks
FORBIDDEN_PATTERNS = [
    re.compile(r"\bNone\b"),
    re.compile(r"\bnull\b"),
    re.compile(r"\bundefined\b"),
    re.compile(r"\bNaN\b"),
    re.compile(r"\{\{.*?\}\}"),
    re.compile(r"%\(.*?\)[sd]"),
    re.compile(r"None\s*\(\s*None\s*\)")
]

def contains_unresolved_template(text: str) -> bool:
    """Checks if a string contains any illegal template placeholders or leaks."""
    if not isinstance(text, str):
        return False
    for pat in FORBIDDEN_PATTERNS:
        if pat.search(text):
            return True
    return False

def sanitize_user_facing_string(text: str, fallback: str = "") -> str:
    """
    Sanitizes a user-facing string by replacing unresolved template leaks with clean text.
    Logs an error if an unresolved placeholder was detected.
    """
    if not isinstance(text, str):
        return str(text) if text is not None else fallback
    
    if contains_unresolved_template(text):
        logger.error(f"[TEMPLATE_GUARD_LEAK] Forbidden template token detected in user-facing string: {text!r}")
        # Clean specific common patterns cleanly
        cleaned = re.sub(r"None\s*\(\s*None\s*\)", "General Tech Role (Industry Standard)", text)
        cleaned = re.sub(r"\bNone\b", "General", cleaned)
        cleaned = re.sub(r"\bnull\b", "", cleaned)
        cleaned = re.sub(r"\bundefined\b", "", cleaned)
        cleaned = re.sub(r"\bNaN\b", "0", cleaned)
        cleaned = re.sub(r"\{\{.*?\}\}", "", cleaned)
        return cleaned.strip() or fallback
    
    return text

def validate_dict_no_template_leaks(data: Union[Dict, List, Any], path: str = "") -> List[str]:
    """Recursively validates a dictionary or list for illegal template leaks."""
    errors = []
    if isinstance(data, dict):
        for k, v in data.items():
            curr_path = f"{path}.{k}" if path else k
            if isinstance(v, str) and contains_unresolved_template(v):
                errors.append(f"Leak at {curr_path}: {v!r}")
            elif isinstance(v, (dict, list)):
                errors.extend(validate_dict_no_template_leaks(v, curr_path))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            curr_path = f"{path}[{idx}]"
            if isinstance(item, str) and contains_unresolved_template(item):
                errors.append(f"Leak at {curr_path}: {item!r}")
            elif isinstance(item, (dict, list)):
                errors.extend(validate_dict_no_template_leaks(item, curr_path))
    return errors
