#!/usr/bin/env python3
"""Run a regression-test-first repair trial in a disposable, networkless Docker sandbox.

The tool never commits, pushes, opens PRs, merges, deploys, or accesses credentials.
The caller must supply separate test and fix patches plus allowlisted test commands.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import time
from typing import Sequence

ALLOWED_ROOTS = {
    ".github/workflows", "agents", "config", "core", "docs", "engine",
    "scripts", "tests", "tools", "web",
}
ALLOWED_ROOT_FILES = {
    "Cargo.toml", "Cargo.lock", "Makefile", "package.json", "package-lock.json",
    "pyproject.toml", "pytest.ini", "requirements.txt", "requirements-dev.txt",
    "setup.cfg", "tox.ini",
}
DENIED_NAMES = {
    ".env", ".env.local", ".env.production", "id_rsa", "id_ed25519",
    "authorized_keys", "credentials.json",
}
SHELL_META = re.compile(r"[;&|<>\n\r\x00]")
DIGEST_IMAGE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
MAX_PATCH_BYTES = 1_000_000
MAX_TIMEOUT_SECONDS = 1_800
MAX_OUTPUT_CHARS = 20_000


def validate_test_command(argv: Sequence[str]) -> list[str]:
    """Accept a narrow set of test runners; never invoke a shell."""
    if not argv or len(argv) > 32 or any(not isinstance(part, str) or not part for part in argv):
        raise ValueError("test command must be a non-empty argv list of at most 32 strings")
    if any(SHELL_META.search(part) for part in argv):
        raise ValueError("shell metacharacters are forbidden")
    allowed = (
        argv[0] == "python" and len(argv) >= 3 and argv[1:3] == ["-m", "unittest"]
        or argv[0] == "python" and len(argv) >= 3 and argv[1:3] == ["-m", "pytest"]
        or argv[0] == "pytest"
        or argv[0] == "node" and len(argv) >= 3 and argv[1] == "--check"
        or argv[0] == "cargo" and len(argv) >= 2 and argv[1] == "test"
    )
    if not allowed:
        raise ValueError("only Python unittest/pytest, Node syntax checks, or Cargo tests are allowed")
    return list(argv)


def validate_patch_paths(patch_text: str) -> None:
    """Reject patch paths outside approved project areas and sensitive files."""
    if len(patch_text.encode("utf-8")) > MAX_PATCH_BYTES:
        raise ValueError("patch exceeds the 1 MB limit")
    seen = False
    for line in patch_text.splitlines():
        if not (line.startswith("--- ") or line.startswith("+++ ")):
            continue
        raw = line[4:].split("\t", 1)[0].strip()
        if raw == "/dev/null":
            continue
        if raw.startswith(("a/", "b/")):
            raw = raw[2:]
        path = PurePosixPath(raw)
        if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError("absolute paths and path traversal are forbidden")
        if any(part.lower() in DENIED_NAMES or part.lower().startswith(".env.") for part in path.parts):
            raise ValueError("patch touches a secret/configuration credential path")
        if path.parts[0] not in ALLOWED_ROOTS and not (
            len(path.parts) == 1 and path.name in ALLOWED_ROOT_FILES
        ):
            raise ValueError("patch path is outside approved project roots")
        if path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
            raise ValueError("patch may not touch private-key material")
        seen = True
    if not seen:
        raise ValueError("patch contains no recognized file paths")


def build_docker_command(
    workspace: str,
    image: str,
    argv: Sequence[str],
    timeout_seconds: int = 300,
) -> list[str]:
    """Build a least-privilege Docker invocation for one test command."""
    safe_argv = validate_test_command(argv)
    if not DIGEST_IMAGE.fullmatch(image):
        raise ValueError("sandbox image must be pinned by a full sha256 digest")
    if not 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise ValueError("timeout must be between 1 and 1800 seconds")
    root = Path(workspace).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("workspace must be a directory")
    return [
        "docker", "run", "--rm",
        "--network", "none",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", "128",
        "--memory", "2g",
        "--cpus", "2",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m",
        "--mount", f"type=bind,src={root},dst=/workspace",
        "--workdir", "/workspace",
        image,
        *safe_argv,
    ]


def _apply_patch(workspace: Path, patch_text: str) -> None:
    validate_patch_paths(patch_text)
    root = workspace.resolve(strict=True)
    for line in patch_text.splitlines():
        if not (line.startswith("--- ") or line.startswith("+++ ")):
            continue
        raw = line[4:].split("\t", 1)[0].strip()
        if raw == "/dev/null":
            continue
        if raw.startswith(("a/", "b/")):
            raw = raw[2:]
        target = root / PurePosixPath(raw)
        current = root
        for part in PurePosixPath(raw).parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("patch may not traverse or replace symbolic links")
        if not target.resolve(strict=False).is_relative_to(root):
            raise ValueError("patch target resolves outside the disposable workspace")
    result = subprocess.run(
        ["git", "apply", "--whitespace=error", "-"],
        cwd=workspace,
        input=patch_text,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
        shell=False,
    )
    if result.returncode:
        raise RuntimeError("patch rejected: " + (result.stderr or "git apply failed")[:2000])


def _redact_output(value: str) -> str:
    value = re.sub(r"(?i)(github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,})", "[REDACTED_TOKEN]", value)
    value = re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)\S+", r"\1[REDACTED]", value)
    value = re.sub(r"(?i)((?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]", value)
    return value[:MAX_OUTPUT_CHARS]


def _run_sandbox(workspace: Path, image: str, argv: Sequence[str], timeout: int) -> dict:
    command = build_docker_command(str(workspace), image, argv, timeout)
    started = time.monotonic()
    try:
        result = subprocess.run(
            command, cwd=workspace, capture_output=True, text=True,
            timeout=timeout, check=False, shell=False,
        )
        return {
            "argv": list(argv),
            "exit_code": result.returncode,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": _redact_output(result.stdout),
            "stderr": _redact_output(result.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": list(argv), "exit_code": 124,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": _redact_output(exc.stdout or "" if isinstance(exc.stdout, str) else ""),
            "stderr": "sandbox command timed out",
        }
    except FileNotFoundError:
        return {
            "argv": list(argv), "exit_code": 127,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": "", "stderr": "Docker executable not found",
        }


def run_trial(
    source: str,
    test_patch: str,
    fix_patch: str,
    regression_argv: Sequence[str],
    suite_argv: Sequence[str],
    image: str,
    timeout_seconds: int = 300,
) -> dict:
    """Prove test fails before fix, then passes after fix and the full suite passes."""
    regression = validate_test_command(regression_argv)
    suite = validate_test_command(suite_argv)
    if not DIGEST_IMAGE.fullmatch(image):
        raise ValueError("sandbox image must be pinned by a full sha256 digest")
    test_text = Path(test_patch).read_text(encoding="utf-8")
    fix_text = Path(fix_patch).read_text(encoding="utf-8")
    validate_patch_paths(test_text)
    validate_patch_paths(fix_text)
    source_root = Path(source).resolve(strict=True)
    if not source_root.is_dir():
        raise ValueError("source must be a directory")

    with tempfile.TemporaryDirectory(prefix="mkaos-ci-repair-") as tmp:
        workspace = Path(tmp) / "workspace"
        shutil.copytree(
            source_root, workspace, symlinks=True,
            ignore=shutil.ignore_patterns(
                ".git", ".env", ".env.*", "memory", "models", ".venv", "node_modules",
                ".aws", ".ssh", ".git-credentials", "credentials*", "secrets*",
                "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa", "id_ed25519",
            ),
        )
        _apply_patch(workspace, test_text)
        before = _run_sandbox(workspace, image, regression, timeout_seconds)
        if before["exit_code"] == 0:
            raise RuntimeError("regression test passed before the fix; test-first proof rejected")
        if before["exit_code"] in {124, 127}:
            raise RuntimeError("baseline test did not complete in the sandbox")
        _apply_patch(workspace, fix_text)
        after = _run_sandbox(workspace, image, regression, timeout_seconds)
        if after["exit_code"] != 0:
            raise RuntimeError("regression test still fails after the fix")
        suite_result = _run_sandbox(workspace, image, suite, timeout_seconds)
        if suite_result["exit_code"] != 0:
            raise RuntimeError("full test suite failed after the fix")
        return {
            "schema_version": 1,
            "status": "passed",
            "source_directory_name": source_root.name,
            "sandbox_image": image,
            "network": "disabled",
            "secrets_mounted": False,
            "merge_or_deploy_performed": False,
            "test_patch_sha256": hashlib.sha256(test_text.encode()).hexdigest(),
            "fix_patch_sha256": hashlib.sha256(fix_text.encode()).hexdigest(),
            "regression_before_fix": before,
            "regression_after_fix": after,
            "full_suite_after_fix": suite_result,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="local checkout copied into a temporary workspace")
    parser.add_argument("--test-patch", required=True, help="unified diff adding the regression test")
    parser.add_argument("--fix-patch", required=True, help="unified diff containing the minimal fix")
    parser.add_argument("--regression-command", required=True, help="JSON argv array, never a shell string")
    parser.add_argument("--suite-command", required=True, help="JSON argv array, never a shell string")
    parser.add_argument("--image", required=True, help="trusted Docker image pinned by sha256 digest")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", required=True, help="path for the evidence JSON report")
    args = parser.parse_args()
    try:
        regression = json.loads(args.regression_command)
        suite = json.loads(args.suite_command)
        if not isinstance(regression, list) or not isinstance(suite, list):
            raise ValueError("commands must be JSON arrays")
        report = run_trial(
            args.source, args.test_patch, args.fix_patch, regression, suite,
            args.image, args.timeout,
        )
        report["source_sha"] = os.environ.get("GITHUB_SHA", "not-provided")
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": report["status"], "output": args.output}))
        return 0
    except Exception as exc:
        failure = {
            "schema_version": 1, "status": "rejected_or_failed",
            "error": _redact_output(str(exc)),
            "merge_or_deploy_performed": False,
        }
        Path(args.output).write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(failure))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
