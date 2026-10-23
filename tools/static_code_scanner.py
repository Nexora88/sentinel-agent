"""Evidence-oriented wrapper for Semgrep static analysis.

The scanner never applies fixes. Findings preserve rule IDs, file/line locations,
severity and a short source excerpt so an operator can verify each result.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class StaticCodeScanner:
    """Run Semgrep when installed; return an explicit unavailable status otherwise."""

    def __init__(self, timeout_seconds: int = 180):
        self.timeout_seconds = max(5, min(int(timeout_seconds), 600))

    @staticmethod
    def _severity(value: str) -> str:
        value = (value or "").upper()
        return value if value in {"ERROR", "WARNING", "INFO"} else "INFO"

    @classmethod
    def parse_json(cls, payload: str) -> dict[str, Any]:
        try:
            data = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            return {"status": "error", "findings": [], "error": "Semgrep returned invalid JSON."}
        findings = []
        for item in data.get("results", []):
            extra = item.get("extra") or {}
            start = item.get("start") or {}
            end = item.get("end") or {}
            findings.append({
                "rule_id": str(item.get("check_id") or "unknown"),
                "severity": cls._severity(extra.get("severity")),
                "message": str(extra.get("message") or "No message supplied."),
                "path": str(item.get("path") or ""),
                "start_line": int(start.get("line") or 0),
                "end_line": int(end.get("line") or start.get("line") or 0),
                "evidence": str(extra.get("lines") or "").strip()[:240],
                "source": "semgrep",
            })
        errors = data.get("errors") or []
        return {
            "status": "completed_with_errors" if errors else "completed",
            "findings": findings,
            "errors": [str(error.get("message") or "Semgrep scan error")[:240] for error in errors[:10]],
        }

    def scan_path(self, target: str | Path) -> dict[str, Any]:
        target_path = Path(target).resolve()
        if not target_path.exists():
            return {"status": "error", "findings": [], "error": f"Target does not exist: {target_path}"}
        executable = shutil.which("semgrep")
        if not executable:
            return {
                "status": "unavailable",
                "findings": [],
                "error": "Semgrep CLI is not installed; install Semgrep to enable deterministic static analysis.",
            }
        command = [
            executable, "scan", "--json", "--config", "auto", "--metrics=off",
            "--quiet", str(target_path),
        ]
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=self.timeout_seconds,
                check=False, shell=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "findings": [], "error": "Semgrep scan exceeded its time limit."}
        except OSError as exc:
            return {"status": "error", "findings": [], "error": f"Could not start Semgrep: {type(exc).__name__}"}
        parsed = self.parse_json(completed.stdout)
        if parsed.get("status") == "error":
            parsed["error"] = parsed.get("error") or f"Semgrep exited with status {completed.returncode}."
            return parsed
        if completed.returncode not in (0, 1) and not parsed.get("findings"):
            parsed["status"] = "error"
            parsed["error"] = f"Semgrep exited with status {completed.returncode}."
            parsed["stderr"] = completed.stderr[-500:]
        return parsed

    @staticmethod
    def format_report(result: dict[str, Any]) -> str:
        lines = ["## Static analysis (Semgrep)", f"Status: {result.get('status', 'unknown')}"]
        if result.get("error"):
            lines.append(f"Notice: {result['error']}")
        for finding in result.get("findings", []):
            location = f"{finding.get('path', '?')}:{finding.get('start_line', 0)}"
            lines.extend([
                f"- [{finding.get('severity', 'INFO')}] {finding.get('rule_id', 'unknown')} — {location}",
                f"  {finding.get('message', '')}",
                f"  Evidence: {finding.get('evidence') or '(no source excerpt supplied)'}",
            ])
        if not result.get("findings") and result.get("status") == "completed":
            lines.append("No findings reported by the configured Semgrep ruleset.")
        for error in result.get("errors", []):
            lines.append(f"Scanner warning: {error}")
        lines.append("Findings require human review; this scanner does not apply fixes or prove exploitability.")
        return "\n".join(lines)
