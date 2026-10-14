"""
Safety layer for Sentinel.
Protects against prompt injection from scraped web content and
blocks any attempt at arbitrary shell / destructive commands.
"""

from __future__ import annotations

import re
from typing import List, Tuple

# Patterns that indicate possible prompt injection or destructive intent
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"you\s+are\s+now\s+",
    r"system\s*:\s*",
    r"new\s+instructions\s*:",
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+\*",
    r"sudo\s+rm",
    r"format\s+c:",
    r"del\s+/[fq]\s+",
    r"drop\s+table",
    r"delete\s+from\s+",
    r"os\.system\s*\(",
    r"subprocess\.(call|run|Popen)",
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__\s*\(",
    r"chmod\s+777",
    r"curl\s+.*\|\s*sh",
    r"wget\s+.*\|\s*sh",
    r"base64\s+-d\s+.*\|\s*sh",
]

# Only these actions are ever allowed to be proposed by agents
ALLOWED_ACTIONS_WHITELIST = {
    "read_code",
    "run_static_analysis",
    "create_report",
    "scan_website",
    "send_notification",
    "modify_files",          # still needs human approval
    "commit_changes",        # still needs human approval
    "push_to_remote",        # still needs human approval
    "create_pull_request",   # still needs human approval
    "open_github_issue",
}

# Hard block — never execute these even if approval somehow exists
FORBIDDEN_SHELL_PATTERNS = [
    r"rm\s+-rf",
    r"rm\s+-r\s+/",
    r"dd\s+if=",
    r"mkfs",
    r":\(\)\s*\{\s*:\|:\s*&\s*\}",  # fork bomb
    r"chmod\s+-R\s+777\s+/",
    r">\s*/dev/sd",
    r"curl\s+.*\|\s*(ba)?sh",
    r"wget\s+.*\|\s*(ba)?sh",
]


def sanitize_web_content(text: str) -> str:
    """Remove or neutralize potential injection payloads from scraped pages."""
    if not text:
        return ""
    cleaned = text
    for pat in INJECTION_PATTERNS:
        cleaned = re.sub(pat, "[FILTERED]", cleaned, flags=re.IGNORECASE)
    # Cap length aggressively for RAG chunks
    return cleaned[:10000]


def contains_injection(text: str) -> bool:
    """Return True if text looks like a prompt injection attempt."""
    lower = text.lower()
    for pat in INJECTION_PATTERNS:
        if re.search(pat, lower, re.IGNORECASE):
            return True
    return False


def is_forbidden_shell(cmd: str) -> bool:
    """Hard block for dangerous shell commands."""
    for pat in FORBIDDEN_SHELL_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return True
    return False


def validate_action(action: str) -> Tuple[bool, str]:
    """Check if an action is in the allowed whitelist."""
    if action not in ALLOWED_ACTIONS_WHITELIST:
        return False, f"Action '{action}' is not in the allowed whitelist."
    return True, "ok"
