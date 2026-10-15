"""
Safety layer for Sentinel.
Protects against prompt injection from scraped web content and
blocks any attempt at arbitrary shell / destructive commands.
Also provides lightweight source credibility heuristics (not a truth oracle).
"""

from __future__ import annotations

import re
from typing import List, Tuple
from urllib.parse import urlparse

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

ALLOWED_ACTIONS_WHITELIST = {
    "read_code",
    "run_static_analysis",
    "create_report",
    "scan_website",
    "send_notification",
    "modify_files",
    "commit_changes",
    "push_to_remote",
    "create_pull_request",
    "open_github_issue",
}

FORBIDDEN_SHELL_PATTERNS = [
    r"rm\s+-rf",
    r"rm\s+-r\s+/",
    r"dd\s+if=",
    r"mkfs",
    r":\(\)\s*\{\s*:\|:\s*&\s*\}",
    r"chmod\s+-R\s+777\s+/",
    r">\s*/dev/sd",
    r"curl\s+.*\|\s*(ba)?sh",
    r"wget\s+.*\|\s*(ba)?sh",
]

# Higher trust domains for research-style ingestion (heuristic only)
HIGHER_TRUST_DOMAINS = {
    "arxiv.org",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "nature.com",
    "science.org",
    "ieee.org",
    "acm.org",
    "github.com",
    "gitlab.com",
    "wikipedia.org",
    "docs.python.org",
    "owasp.org",
    "nist.gov",
    "cve.mitre.org",
}

LOWER_TRUST_HINTS = [
    r"clickbait",
    r"you won't believe",
    r"doctors hate",
    r"miracle cure",
    r"100% guaranteed",
    r"secret they don't want",
]


def sanitize_web_content(text: str) -> str:
    if not text:
        return ""
    cleaned = text
    for pat in INJECTION_PATTERNS:
        cleaned = re.sub(pat, "[FILTERED]", cleaned, flags=re.IGNORECASE)
    return cleaned[:10000]


def contains_injection(text: str) -> bool:
    lower = text.lower()
    for pat in INJECTION_PATTERNS:
        if re.search(pat, lower, re.IGNORECASE):
            return True
    return False


def is_forbidden_shell(cmd: str) -> bool:
    for pat in FORBIDDEN_SHELL_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return True
    return False


def validate_action(action: str) -> Tuple[bool, str]:
    if action not in ALLOWED_ACTIONS_WHITELIST:
        return False, f"Action '{action}' is not in the allowed whitelist."
    return True, "ok"


def source_credibility(url: str, text: str = "") -> Tuple[str, float]:
    """
    Return (label, score 0-1). Heuristic only — not a fact-checker.
    """
    try:
        host = urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        host = ""
    score = 0.45
    if any(host == d or host.endswith("." + d) for d in HIGHER_TRUST_DOMAINS):
        score = 0.8
    if host.endswith(".gov") or host.endswith(".edu"):
        score = max(score, 0.75)
    blob = (text or "")[:2000].lower()
    for pat in LOWER_TRUST_HINTS:
        if re.search(pat, blob):
            score = min(score, 0.25)
    if score >= 0.7:
        return "higher", score
    if score <= 0.3:
        return "lower", score
    return "medium", score
