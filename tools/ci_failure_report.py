#!/usr/bin/env python3
"""Build a bounded, redacted CI failure report from untrusted workflow logs.

This tool does not execute log-provided commands, check out pull-request code,
call an LLM, modify files, or create/merge pull requests.
"""
from __future__ import annotations

import argparse
import re
import sys

MAX_INPUT_CHARS = 250_000
REDACTIONS = [
    (re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)\S+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,})"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"(?i)(AKIA[0-9A-Z]{16})"), "[REDACTED_AWS_ACCESS_KEY]"),
    (re.compile(r"(?i)((?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[=:]\s*)[^\s,;]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(https?://[^\s/:@]+:)[^\s/@]+@"), r"\1[REDACTED]@"),
]


def redact(text: str) -> str:
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def build_report(run_id: str, head_sha: str, raw_log: str) -> str:
    clipped = raw_log[:MAX_INPUT_CHARS]
    was_clipped = len(raw_log) > MAX_INPUT_CHARS
    safe = redact(clipped)
    return (
        "# CI failure evidence (automatically captured)\n\n"
        f"- Workflow run ID: {run_id}\n"
        f"- Source commit: {head_sha}\n"
        "- Execution status: failed workflow; this report is diagnostic evidence only\n"
        "- Source checkout: not performed by the evidence collector\n"
        "- Automated code changes, commits, PRs, merge, and deployment: not performed\n"
        f"- Log truncated: {'yes' if was_clipped else 'no'}\n\n"
        "## Sanitized failed-job log excerpt\n\n"
        "```text\n" + safe + "\n```\n\n"
        "## Required next steps\n\n"
        "1. Reproduce the failure in a disposable, network-restricted environment.\n"
        "2. Add a regression test and demonstrate it fails before the fix.\n"
        "3. Apply the smallest patch; rerun the regression test and full CI.\n"
        "4. Attach command output and commit SHA to a draft PR for human review.\n"
        "5. Keep merge and deployment behind explicit human approval.\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--head-sha", required=True)
    args = parser.parse_args()
    report = build_report(args.run_id, args.head_sha, sys.stdin.read(MAX_INPUT_CHARS + 1))
    sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
