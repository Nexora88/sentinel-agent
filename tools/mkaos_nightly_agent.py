"""Read-only nightly audit runner for explicitly allowlisted MKAOS projects.

This tool runs a fixed set of checks; project configuration cannot inject shell commands.
It never edits source files, creates commits, pushes, or merges changes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CHECKS = {"python_compile", "python_tests", "rust_tests", "git_diff_check", "secret_pattern_audit"}
SECRET_PATTERNS = (
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{40,})\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key_header", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
)


def run_command(argv: list[str], cwd: Path, timeout: int = 600) -> dict:
    try:
        completed = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
            check=False, shell=False, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        return {
            "status": "passed" if completed.returncode == 0 else "failed",
            "exit_code": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
    except subprocess.TimeoutExpired:
        return {"status": "failed", "exit_code": None, "stdout": "", "stderr": f"Timed out after {timeout}s"}
    except OSError as exc:
        return {"status": "unavailable", "exit_code": None, "stdout": "", "stderr": str(exc)[:1000]}


def secret_pattern_audit(project: Path) -> dict:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"], cwd=str(project), capture_output=True,
            check=True, shell=False, timeout=20,
        )
        names = [item.decode("utf-8", "replace") for item in result.stdout.split(b"\0") if item]
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "unavailable", "findings": [], "detail": f"Cannot enumerate tracked files: {type(exc).__name__}"}
    findings = []
    skip_parts = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__"}
    for name in names:
        path = project / name
        if any(part in skip_parts for part in Path(name).parts):
            continue
        if Path(name).name in {".env.example", "requirements.lock", "poetry.lock", "uv.lock"}:
            continue
        try:
            if not path.is_file() or path.stat().st_size > 1_000_000:
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for label, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(content):
                line = content.count("\n", 0, match.start()) + 1
                findings.append({"rule": label, "path": name, "line": line,
                                 "evidence": "[redacted pattern; inspect locally]"})
                if len(findings) >= 100:
                    break
            if len(findings) >= 100:
                break
        if len(findings) >= 100:
            break
    return {"status": "failed" if findings else "passed", "findings": findings,
            "detail": "Pattern matches require human review; this is not a full secret scanner."}


def run_check(check: str, project: Path) -> dict:
    if check == "python_compile":
        targets = [name for name in ("agents", "core", "scripts", "tools", "web") if (project / name).exists()]
        return run_command([sys.executable, "-m", "compileall", "-q", *targets], project, 180)
    if check == "python_tests":
        if not (project / "tests").is_dir():
            return {"status": "unavailable", "detail": "No tests/ directory"}
        return run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], project, 900)
    if check == "rust_tests":
        manifest = project / "engine" / "mkaos-inference" / "Cargo.toml"
        if not manifest.is_file():
            return {"status": "unavailable", "detail": "Rust inference manifest not found"}
        return run_command(["cargo", "test", "--manifest-path", str(manifest), "--all-targets"], project, 900)
    if check == "git_diff_check":
        return run_command(["git", "diff", "--check"], project, 60)
    if check == "secret_pattern_audit":
        return secret_pattern_audit(project)
    return {"status": "failed", "detail": "Unsupported check rejected"}


def run_audit(config_path: Path, workspace: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1 or not isinstance(config.get("projects"), list):
        raise ValueError("Unsupported allowlist schema")
    report = {
        "project": "MKAOS",
        "report_type": "night-watch-agent-audit",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": config.get("policy", "read_only_audit"),
        "workspace": str(workspace),
        "projects": [],
    }
    for entry in config["projects"]:
        if not isinstance(entry, dict) or not entry.get("enabled", False):
            continue
        project_id = str(entry.get("id", ""))[:100]
        relative = Path(str(entry.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            report["projects"].append({"id": project_id, "status": "blocked",
                                       "reason": "Project path must remain relative and cannot traverse parents."})
            continue
        project = (workspace / relative).resolve()
        try:
            project.relative_to(workspace.resolve())
        except ValueError:
            report["projects"].append({"id": project_id, "status": "blocked",
                                       "reason": "Project path escaped the configured workspace."})
            continue
        if not project.is_dir():
            report["projects"].append({"id": project_id, "status": "unavailable",
                                       "reason": "Allowlisted project directory does not exist."})
            continue
        requested = entry.get("checks", [])
        invalid = [name for name in requested if name not in CHECKS]
        results = {name: run_check(name, project) for name in requested if name in CHECKS}
        failed = any(value.get("status") == "failed" for value in results.values())
        report["projects"].append({
            "id": project_id, "path": str(relative), "status": "failed" if failed or invalid else "completed",
            "invalid_checks": invalid, "checks": results,
        })
    report["overall_status"] = "failed" if any(p.get("status") in {"failed", "blocked"} for p in report["projects"]) else "completed"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/mkaos-agent-projects.json")
    parser.add_argument("--output", default="artifacts/mkaos-night-watch-report.json")
    parser.add_argument("--workspace", default=".")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = (Path.cwd() / config_path).resolve()
    try:
        report = run_audit(config_path, workspace)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Night-watch audit could not start: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    output = Path(args.output)
    if not output.is_absolute():
        output = Path.cwd() / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "overall_status": report["overall_status"],
                      "projects": len(report["projects"])}, ensure_ascii=False))
    return 1 if report["overall_status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
