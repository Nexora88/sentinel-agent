"""
Local license / copyright hygiene checker.
Advisory only — does not contact registries or file legal claims.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

LICENSE_HINTS = [
    (r"MIT License", "MIT"),
    (r"Apache License,?\s*Version 2", "Apache-2.0"),
    (r"GNU GENERAL PUBLIC LICENSE", "GPL"),
    (r"BSD [23]-Clause", "BSD"),
    (r"Mozilla Public License", "MPL-2.0"),
    (r"Copyright \(c\)", "copyright-notice"),
    (r"All rights reserved", "all-rights-reserved"),
]

SPDX_RE = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9.\-+]+)")


class LicenseChecker:
    def scan_tree(self, root: str = ".", max_files: int = 200) -> Dict:
        root_p = Path(root)
        findings: List[Dict] = []
        has_license_file = any(
            (root_p / name).exists()
            for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")
        )
        checked = 0
        for path in root_p.rglob("*"):
            if checked >= max_files:
                break
            if not path.is_file():
                continue
            if path.suffix.lower() not in {
                ".py", ".js", ".ts", ".go", ".rs", ".java", ".md", ".txt"
            }:
                continue
            if any(x in path.parts for x in (".git", "node_modules", "venv", "__pycache__", "memory")):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:4000]
            except Exception:
                continue
            checked += 1
            spdx = SPDX_RE.search(text)
            licenses = []
            if spdx:
                licenses.append(spdx.group(1))
            for pat, name in LICENSE_HINTS:
                if re.search(pat, text, re.IGNORECASE):
                    licenses.append(name)
            if licenses:
                findings.append({"file": str(path), "hints": sorted(set(licenses))})

        return {
            "root_license_file": has_license_file,
            "files_with_notices": len(findings),
            "checked_files": checked,
            "samples": findings[:30],
            "advice": (
                "Root LICENSE present."
                if has_license_file
                else "No LICENSE file at repo root — consider adding one before publishing."
            ),
        }

    def format_report(self, result: Dict) -> str:
        lines = [
            "📜 License / Copyright hygiene (advisory)",
            f"Root LICENSE: {'yes' if result.get('root_license_file') else 'NO'}",
            f"Files checked: {result.get('checked_files')}",
            f"Files with notices: {result.get('files_with_notices')}",
            result.get("advice", ""),
        ]
        for s in result.get("samples", [])[:10]:
            lines.append(f"  • {s['file']}: {', '.join(s['hints'])}")
        return "\n".join(lines)
