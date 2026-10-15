"""Heuristic local code-cleanliness scan; similarity signals are not legal conclusions."""
from __future__ import annotations
import hashlib, re
from pathlib import Path

NOTICE_PATTERNS = {
    "GPL": re.compile(r"GNU GENERAL PUBLIC LICENSE|SPDX-License-Identifier:\s*GPL", re.I),
    "AGPL": re.compile(r"GNU AFFERO GENERAL PUBLIC LICENSE|SPDX-License-Identifier:\s*AGPL", re.I),
    "copyright": re.compile(r"copyright|all rights reserved", re.I),
}
def scan_code_cleanliness(root: str = ".", max_files: int = 300) -> dict:
    root_path = Path(root).resolve()
    findings, checked = [], 0
    for path in root_path.rglob("*"):
        if checked >= max_files: break
        if not path.is_file() or any(p in {".git","node_modules","venv","__pycache__","memory"} for p in path.parts): continue
        if path.suffix.lower() not in {".py",".js",".ts",".jsx",".tsx",".go",".rs",".java",".md"}: continue
        try: body = path.read_text(encoding="utf-8", errors="ignore")[:200000]
        except OSError: continue
        checked += 1
        hints = [name for name, pattern in NOTICE_PATTERNS.items() if pattern.search(body[:6000])]
        if hints:
            findings.append({"file": str(path.relative_to(root_path)), "hints": hints,
                             "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()})
    return {"checked_files": checked, "notice_files": len(findings), "findings": findings[:100],
            "policy": "Heuristic only. No web corpus comparison; no plagiarism percentage or legal conclusion."}
