"""Read-only local workspace scanner. Findings are redacted; files are never modified."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SKIP_DIRS = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache", "dist", "build"}
SKIP_NAMES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519", "credentials.json", "secrets.json"}
MAX_FILE_BYTES = 512 * 1024
DEFAULT_MAX_FILES = 10_000
PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("generic-secret-assignment", re.compile(r"""(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*["'][^"'\s]{8,}["']""")),
]

def _ignored(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    return bool(parts & SKIP_DIRS) or name in SKIP_NAMES or name.startswith(".env.") or name.endswith((".pem", ".p12", ".pfx", ".key", ".sqlite", ".sqlite3", ".db"))

def scan_workspace(target: str | Path = ".", max_files: int = DEFAULT_MAX_FILES) -> dict[str, Any]:
    """Inspect bounded text files under target without following symlinks or changing data."""
    root = Path(target).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Scan target must be a directory.")
    if max_files < 1 or max_files > DEFAULT_MAX_FILES:
        raise ValueError(f"max_files must be between 1 and {DEFAULT_MAX_FILES}.")
    scanned = 0
    skipped = 0
    findings: list[dict[str, Any]] = []
    truncated = False
    for candidate in root.rglob("*"):
        try:
            relative = candidate.relative_to(root)
            if _ignored(relative):
                if candidate.is_dir():
                    # rglob may still enumerate descendants; each is filtered by its path.
                    continue
                skipped += 1
                continue
            if candidate.is_symlink() or not candidate.is_file():
                continue
            if candidate.stat().st_size > MAX_FILE_BYTES:
                skipped += 1
                continue
            if scanned >= max_files:
                truncated = True
                break
            try:
                content = candidate.read_text(encoding="utf-8")
            except (UnicodeError, OSError):
                skipped += 1
                continue
            scanned += 1
            for label, pattern in PATTERNS:
                for match in pattern.finditer(content):
                    line = content.count("\n", 0, match.start()) + 1
                    findings.append({
                        "rule": label,
                        "path": relative.as_posix(),
                        "line": line,
                        "severity": "high" if label in {"private-key", "github-token", "aws-access-key"} else "medium",
                        "evidence": "[REDACTED]",
                    })
        except (OSError, ValueError):
            skipped += 1
    return {
        "scanner": "mkaos-readonly-scanner",
        "version": "0.1.0",
        "target": str(root),
        "read_only": True,
        "files_scanned": scanned,
        "files_skipped": skipped,
        "truncated": truncated,
        "findings": findings,
        "disclaimer": "Heuristic scan only; no finding does not prove a workspace is secure.",
    }
