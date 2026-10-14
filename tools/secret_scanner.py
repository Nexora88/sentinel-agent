"""
Secret Scanner — defensive only.
Finds hardcoded API keys, tokens, passwords in code before they get committed.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

# Common secret patterns (high precision)
SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]([a-zA-Z0-9_\-]{20,})['\"]", "api_key"),
    (r"(?i)(secret[_-]?key|secretkey)\s*[:=]\s*['\"]([a-zA-Z0-9_\-]{16,})['\"]", "secret_key"),
    (r"(?i)(access[_-]?token|accesstoken)\s*[:=]\s*['\"]([a-zA-Z0-9_\-\.]{20,})['\"]", "access_token"),
    (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]([^'\"]{8,})['\"]", "password"),
    (r"ghp_[a-zA-Z0-9]{36}", "github_pat"),
    (r"gho_[a-zA-Z0-9]{36}", "github_oauth"),
    (r"sk-[a-zA-Z0-9]{32,}", "openai_style_key"),
    (r"AKIA[0-9A-Z]{16}", "aws_access_key"),
    (r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['\"]([a-zA-Z0-9/+=]{40})['\"]", "aws_secret"),
    (r"-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----", "private_key"),
    (r"(?i)(db_password|database_password)\s*[:=]\s*['\"]([^'\"]+)['\"]", "db_password"),
]

SKIP_DIRS = {".git", "venv", ".venv", "node_modules", "__pycache__", ".mypy_cache", "memory", ".pytest_cache"}
SKIP_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".zip", ".pyc"}


class SecretScanner:
    def scan_text(self, content: str, source: str = "unknown") -> List[Dict]:
        findings = []
        for pattern, kind in SECRET_PATTERNS:
            for match in re.finditer(pattern, content):
                # Redact the actual secret in the report
                snippet = match.group(0)
                if len(snippet) > 40:
                    snippet = snippet[:20] + "..." + snippet[-8:]
                findings.append({
                    "type": kind,
                    "source": source,
                    "snippet": snippet,
                    "line": content[:match.start()].count("\n") + 1,
                })
        return findings

    def scan_file(self, path: Path) -> List[Dict]:
        if path.suffix.lower() in SKIP_EXTS:
            return []
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []
        return self.scan_text(text, source=str(path))

    def scan_directory(self, root: str | Path, max_files: int = 200) -> List[Dict]:
        root = Path(root)
        all_findings = []
        count = 0
        for p in root.rglob("*"):
            if count >= max_files:
                break
            if not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            findings = self.scan_file(p)
            all_findings.extend(findings)
            count += 1
        return all_findings

    def format_report(self, findings: List[Dict]) -> str:
        if not findings:
            return "✅ Gizli anahtar / credential bulunamadı."
        lines = [f"⚠️  {len(findings)} olası gizli anahtar bulundu:\n"]
        for f in findings[:30]:
            lines.append(f"  [{f['type']}] {f['source']}:{f['line']} → {f['snippet']}")
        if len(findings) > 30:
            lines.append(f"  ... ve {len(findings)-30} tane daha")
        lines.append("\nBu değerleri koddan çıkarıp ortam değişkenine taşı.")
        return "\n".join(lines)
