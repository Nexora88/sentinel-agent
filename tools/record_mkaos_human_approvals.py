#!/usr/bin/env python3
"""İnsan onay defteri — eğitim kapısı için zorunlu.

Her source_id için karar: approve | reject | needs_review
Tüm kayıtlar approve olmadan eğitim başlatılmamalıdır.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DECISIONS = {"approve", "reject", "needs_review"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_ledger(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        out[row["source_id"]] = row
    return out


def write_ledger(path: Path, rows: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(rows[k], ensure_ascii=False, sort_keys=True)
        for k in sorted(rows)
    ]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def load_source_ids(records_path: Path) -> list[str]:
    ids: list[str] = []
    for line in records_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        ids.append(obj["source_id"])
    return ids


def gate_status(ledger: dict[str, dict], required_ids: list[str]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    for sid in required_ids:
        row = ledger.get(sid)
        if not row:
            issues.append(f"{sid}: no human decision")
            continue
        if row.get("decision") != "approve":
            issues.append(f"{sid}: decision={row.get('decision')}")
        if not isinstance(row.get("reviewer_id"), str) or not row["reviewer_id"].strip():
            issues.append(f"{sid}: missing reviewer_id")
        if not isinstance(row.get("content_sha256"), str) or len(row["content_sha256"]) != 64:
            issues.append(f"{sid}: missing content_sha256 pin")
    return not issues, issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=Path("data/mkaos-tr-seed-12/records.jsonl"))
    parser.add_argument("--ledger", type=Path, default=Path("data/mkaos-tr-seed-12/approvals.jsonl"))
    parser.add_argument("--source-id", type=str, default=None)
    parser.add_argument("--decision", choices=sorted(DECISIONS), default=None)
    parser.add_argument("--reviewer-id", type=str, default="local-owner")
    parser.add_argument("--notes", type=str, default="")
    parser.add_argument("--approve-all", action="store_true", help="mark every record approve (explicit human action)")
    parser.add_argument("--check-gate", action="store_true", help="exit 0 only if all approved")
    parser.add_argument("--init-needs-review", action="store_true", help="create needs_review rows for missing ids")
    args = parser.parse_args(argv)

    try:
        required = load_source_ids(args.records)
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"LEDGER_FAILED: {exc}", file=sys.stderr)
        return 2

    # content hashes from records
    content_hashes: dict[str, str] = {}
    for line in args.records.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        payload = (obj["prompt"].strip() + "\n" + obj["response"].strip()).encode("utf-8")
        content_hashes[obj["source_id"]] = hashlib.sha256(payload).hexdigest()

    ledger = load_ledger(args.ledger)

    if args.init_needs_review:
        for sid in required:
            if sid not in ledger:
                ledger[sid] = {
                    "source_id": sid,
                    "decision": "needs_review",
                    "reviewer_id": args.reviewer_id,
                    "content_sha256": content_hashes[sid],
                    "decided_at_utc": _now(),
                    "notes": "initialized",
                }
        write_ledger(args.ledger, ledger)
        print(f"INIT_OK count={len(ledger)}")

    if args.approve_all:
        for sid in required:
            ledger[sid] = {
                "source_id": sid,
                "decision": "approve",
                "reviewer_id": args.reviewer_id,
                "content_sha256": content_hashes[sid],
                "decided_at_utc": _now(),
                "notes": args.notes or "approve-all",
            }
        write_ledger(args.ledger, ledger)
        print(f"APPROVE_ALL_OK count={len(required)}")

    if args.source_id and args.decision:
        if args.source_id not in content_hashes:
            print(f"unknown source_id: {args.source_id}", file=sys.stderr)
            return 2
        ledger[args.source_id] = {
            "source_id": args.source_id,
            "decision": args.decision,
            "reviewer_id": args.reviewer_id,
            "content_sha256": content_hashes[args.source_id],
            "decided_at_utc": _now(),
            "notes": args.notes,
        }
        write_ledger(args.ledger, ledger)
        print(f"RECORDED {args.source_id}={args.decision}")

    ok, issues = gate_status(ledger, required)
    if args.check_gate:
        if ok:
            print("TRAINING_GATE_OPEN")
            return 0
        print("TRAINING_GATE_CLOSED")
        for issue in issues:
            print(issue, file=sys.stderr)
        return 2

    print(f"ledger={args.ledger} decisions={len(ledger)} gate_open={ok}")
    if not ok:
        for issue in issues[:20]:
            print(f"  - {issue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
