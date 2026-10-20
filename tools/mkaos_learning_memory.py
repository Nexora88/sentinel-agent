"""Bounded, privacy-conscious memory for the MKAOS Night Watch.

Stores failure fingerprints and regression-test obligations, never raw logs or source.
It does not edit project code or generate/merge patches.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_ENTRIES = 500


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(project_id: str, check_name: str, rule: str = "check_failed") -> str:
    return f"{project_id[:100]}::{check_name[:100]}::{rule[:100]}"


def _failed_items(report: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for project in report.get("projects", []):
        project_id = str(project.get("id", "unknown"))[:100]
        for check_name, result in project.get("checks", {}).items():
            if result.get("status") == "failed":
                items.append({"project_id": project_id, "check": str(check_name)[:100], "rule": "check_failed"})
            # Secret audit findings are recorded by rule/path, without matching text or secret material.
            for finding in result.get("findings", []):
                if isinstance(finding, dict):
                    items.append({"project_id": project_id, "check": str(check_name)[:100],
                                  "rule": str(finding.get("rule", "finding"))[:100]})
        for invalid in project.get("invalid_checks", []):
            items.append({"project_id": project_id, "check": str(invalid)[:100], "rule": "invalid_check_configuration"})
        if project.get("status") in {"failed", "blocked"} and not project.get("checks"):
            items.append({"project_id": project_id, "check": "project_scope", "rule": str(project.get("status"))})
    # Deterministic deduplication so one report cannot inflate counts from duplicate findings.
    unique = {_fingerprint(x["project_id"], x["check"], x["rule"]): x for x in items}
    return [unique[key] for key in sorted(unique)]


def update_memory(previous: dict[str, Any] | None, report: dict[str, Any], now: str | None = None) -> dict[str, Any]:
    """Merge a Night Watch report into the bounded learning ledger."""
    timestamp = now or utc_now()
    if previous and previous.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported learning-memory schema version")
    entries: dict[str, dict[str, Any]] = {}
    for entry in (previous or {}).get("entries", []):
        if isinstance(entry, dict) and isinstance(entry.get("fingerprint"), str):
            entries[entry["fingerprint"]] = dict(entry)

    current = { _fingerprint(x["project_id"], x["check"], x["rule"]): x for x in _failed_items(report) }
    rechecked: list[dict[str, str]] = []
    for fingerprint, entry in entries.items():
        if fingerprint in current:
            rechecked.append({"fingerprint": fingerprint, "result": "recurring_failure"})
        else:
            rechecked.append({"fingerprint": fingerprint, "result": "not_seen_in_current_report"})

    for fingerprint, item in current.items():
        old = entries.get(fingerprint, {})
        first_seen = old.get("first_seen_utc", timestamp)
        entries[fingerprint] = {
            "fingerprint": fingerprint,
            "project_id": item["project_id"],
            "check": item["check"],
            "rule": item["rule"],
            "first_seen_utc": first_seen,
            "last_seen_utc": timestamp,
            "occurrences": int(old.get("occurrences", 0)) + 1,
            "last_status": "failed",
            "regression_test_required": True,
            "regression_test_guidance": (
                "Reproduce the failure with a deterministic test; assert the observed failure is fixed; "
                "keep the test in the relevant test suite and run it on every Night Watch cycle."
            ),
            "last_commit_sha": str(report.get("commit_sha", ""))[:80],
        }

    # Preserve historical records; mark those absent from this run as cleared only if their check
    # actually ran and passed. Missing/unavailable checks must not be mistaken for a fix.
    statuses: dict[str, str] = {}
    for project in report.get("projects", []):
        project_id = str(project.get("id", "unknown"))[:100]
        for check_name, result in project.get("checks", {}).items():
            statuses[_fingerprint(project_id, str(check_name), "check_failed")] = str(result.get("status", "unknown"))
            for fingerprint, entry in entries.items():
                if entry.get("project_id") == project_id and entry.get("check") == check_name and entry.get("rule") not in {"check_failed"}:
                    statuses[fingerprint] = "failed" if any(
                        f.get("rule") == entry.get("rule") for f in result.get("findings", []) if isinstance(f, dict)
                    ) else str(result.get("status", "unknown"))
    for fingerprint, entry in entries.items():
        if fingerprint in current:
            continue
        status = statuses.get(fingerprint)
        if status == "passed":
            entry["last_status"] = "cleared_on_recheck"
            entry["last_rechecked_utc"] = timestamp
        elif status:
            entry["last_status"] = "still_unverified" if status in {"unavailable", "unknown"} else "finding_not_reproduced"
            entry["last_rechecked_utc"] = timestamp
        # Otherwise keep the last status; the check may not have been configured/run.

    previous_fingerprints = {e.get("fingerprint") for e in (previous or {}).get("entries", []) if isinstance(e, dict)}
    recurring = sum(1 for key in current if key in previous_fingerprints)
    ordered = sorted(entries.values(), key=lambda e: (e.get("last_seen_utc", ""), e.get("fingerprint", "")), reverse=True)
    ordered = ordered[:MAX_ENTRIES]
    return {
        "schema_version": SCHEMA_VERSION,
        "project": "MKAOS",
        "updated_at_utc": timestamp,
        "policy": "bounded_failure_memory; no_raw_logs; no_source_edits; no_auto_merge",
        "entries": ordered,
        "summary": {
            "known_failure_fingerprints": len(ordered),
            "current_failure_fingerprints": len(current),
            "recurring_failures": recurring,
            "regression_tests_required": sum(1 for e in ordered if e.get("regression_test_required")),
        },
        "rechecked_history": rechecked[:MAX_ENTRIES],
    }


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Learning memory must be a JSON object")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="artifacts/mkaos-night-watch-report.json")
    parser.add_argument("--memory", default="artifacts/mkaos-learning-memory.json")
    parser.add_argument("--output", default="artifacts/mkaos-learning-memory-report.json")
    args = parser.parse_args()
    report = load_json(Path(args.report))
    if report is None:
        raise SystemExit(f"Night Watch report not found: {args.report}")
    previous = load_json(Path(args.memory))
    memory = update_memory(previous, report)
    write_json_atomic(Path(args.memory), memory)
    write_json_atomic(Path(args.output), {
        "report_type": "mkaos-learning-memory-summary",
        "updated_at_utc": memory["updated_at_utc"],
        "summary": memory["summary"],
        "rechecked_history": memory["rechecked_history"],
        "policy": memory["policy"],
    })
    print(json.dumps(memory["summary"], ensure_ascii=False))
    return 1 if report.get("overall_status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
