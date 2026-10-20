"""Validate a proposed MKAOS patch in an isolated Git worktree.

The patch must be supplied explicitly (for example, by a coding model or maintainer).
This tool does not invent fixes, execute patch-supplied commands, or merge to main.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def run(argv: list[str], cwd: Path, timeout: int = 600) -> dict:
    try:
        proc = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                              timeout=timeout, shell=False)
        return {"status": "passed" if proc.returncode == 0 else "failed",
                "exit_code": proc.returncode,
                "stdout": proc.stdout[-3000:], "stderr": proc.stderr[-3000:]}
    except subprocess.TimeoutExpired:
        return {"status": "failed", "exit_code": None, "stdout": "",
                "stderr": f"Timed out after {timeout}s"}
    except OSError as exc:
        return {"status": "unavailable", "exit_code": None, "stdout": "",
                "stderr": type(exc).__name__}


def validate(repo: Path, patch: Path, base_ref: str, output: Path) -> int:
    repo = repo.resolve()
    patch = patch.resolve()
    output = output.resolve()
    if not (repo / ".git").exists():
        raise ValueError("repo must be a Git working tree")
    if not patch.is_file() or patch.stat().st_size > 5_000_000:
        raise ValueError("patch must be a readable file no larger than 5 MB")
    if not base_ref or base_ref.startswith("-") or any(c in base_ref for c in "\n\r\0"):
        raise ValueError("invalid base ref")
    status = run(["git", "status", "--porcelain"], repo, 30)
    if status["status"] != "passed":
        raise RuntimeError("Cannot inspect repository status")
    if status["stdout"].strip():
        raise ValueError("Repository must be clean before isolated validation")
    base = run(["git", "rev-parse", "--verify", f"{base_ref}^{{commit}}"], repo, 30)
    if base["status"] != "passed":
        raise ValueError("base_ref must resolve to an existing commit")
    commit = base["stdout"].strip()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": commit, "patch_name": patch.name,
        "policy": "isolated validation only; no push or merge",
        "checks": {}, "overall_status": "failed",
    }
    with tempfile.TemporaryDirectory(prefix="mkaos-agent-") as tmp:
        worktree = Path(tmp) / "worktree"
        result = run(["git", "worktree", "add", "--detach", str(worktree), commit], repo, 120)
        report["checks"]["create_worktree"] = result
        if result["status"] != "passed":
            output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            return 1
        try:
            check = run(["git", "apply", "--check", str(patch)], worktree, 60)
            report["checks"]["patch_check"] = check
            if check["status"] == "passed":
                report["checks"]["apply_patch"] = run(["git", "apply", str(patch)], worktree, 60)
            if report["checks"].get("apply_patch", {}).get("status") == "passed":
                report["checks"]["python_compile"] = run(
                    [sys.executable, "-m", "compileall", "-q", "agents", "core", "scripts", "tools", "web"],
                    worktree, 180)
                report["checks"]["python_tests"] = run(
                    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                    worktree, 900)
                manifest = worktree / "engine" / "mkaos-inference" / "Cargo.toml"
                if manifest.is_file():
                    report["checks"]["rust_tests"] = run(
                        ["cargo", "test", "--manifest-path", str(manifest), "--all-targets"],
                        worktree, 900)
                report["checks"]["diff_check"] = run(["git", "diff", "--check"], worktree, 60)
        finally:
            run(["git", "worktree", "remove", "--force", str(worktree)], repo, 60)
            run(["git", "worktree", "prune"], repo, 30)
    statuses = [v.get("status") for v in report["checks"].values()]
    required = {"create_worktree", "patch_check", "apply_patch", "python_compile", "python_tests", "diff_check"}
    report["overall_status"] = (
        "passed" if required.issubset(report["checks"]) and all(report["checks"][k]["status"] == "passed" for k in required)
        and all(v == "passed" for v in statuses) else "failed"
    )
    report["note"] = "A passing report validates this patch only; human review and explicit PR publication remain required."
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        output.chmod(0o600)
    except OSError:
        pass
    return 0 if report["overall_status"] == "passed" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Authorized local Git working tree")
    parser.add_argument("--patch", required=True, help="Explicit unified diff file")
    parser.add_argument("--base-ref", default="HEAD")
    parser.add_argument("--output", default="artifacts/mkaos-coding-agent-report.json")
    args = parser.parse_args()
    try:
        return validate(Path(args.repo), Path(args.patch), args.base_ref, Path(args.output))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Supervised patch validation stopped: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
