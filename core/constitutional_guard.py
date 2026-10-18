"""Small deterministic output guard for obvious credential leakage.

This is a narrow security backstop, not a truth oracle, political filter, or proof
that a model is unbiased. It deliberately does not infer historical truth or judge
claims based on nationality; those require sources and human/domain review.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardResult:
    text: str
    findings: tuple[str, ...]


_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key_block", re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----.*?"
        r"-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", re.S)),
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("openai_style_secret", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("bearer_credential", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{24,}")),
)


def guard_output(text: str) -> GuardResult:
    """Redact only high-confidence secret-shaped strings; preserve other output."""
    guarded = str(text)
    findings: list[str] = []
    for label, pattern in _PATTERNS:
        guarded, count = pattern.subn("[REDACTED: possible secret]", guarded)
        if count:
            findings.append(f"{label}:{count}")
    return GuardResult(guarded, tuple(findings))
