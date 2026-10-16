#!/usr/bin/env python3
"""Offline audit of a local Turkish text JSONL before any MKAOS training.

This tool does not download, upload, rewrite, approve, or train on data. It reports
file/text hashes, duplicate candidates, common PII indicators, and split leakage.
Human and legal review are still mandatory; regex checks cannot prove data is safe.
Expected JSONL fields: sample_id, text, source_id, source_uri, document_group,
license_id, split (train/validation/test), human_review, pii_status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
URL_AUTH_RE = re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*[^\s,;]{6,}")
TR_ID_RE = re.compile(r"(?<!\d)\d{11}(?!\d)")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?90[ .-]?)?(?:0[ .-]?)?5\d{2}[ .-]?\d{3}[ .-]?\d{2}[ .-]?\d{2}(?!\d)")
SPLITS = {"train", "validation", "test"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_for_duplicate_check(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(value.split())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Local UTF-8 JSONL; never uploaded")
    parser.add_argument("--report", required=True, type=Path, help="New JSON report path; never overwritten")
    args = parser.parse_args()

    try:
        raw = args.input.read_bytes()
        decoded = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"ERROR: cannot read UTF-8 corpus: {exc}", file=sys.stderr)
        return 2

    records: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    normalized_hashes: dict[str, int] = {}
    groups_to_splits: dict[str, set[str]] = defaultdict(set)
    pii_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    duplicate_rows: list[int] = []
    for line_no, line in enumerate(decoded.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            rejects.append({"line": line_no, "reason": "invalid_json"})
            continue
        if not isinstance(row, dict):
            rejects.append({"line": line_no, "reason": "record_not_object"})
            continue
        required = ("sample_id", "text", "source_id", "source_uri", "document_group",
                    "license_id", "split", "human_review", "pii_status")
        missing = [key for key in required if not isinstance(row.get(key), str) or not row[key].strip()]
        if missing:
            rejects.append({"line": line_no, "reason": "missing_or_empty_fields", "fields": missing})
            continue
        sample_id = row["sample_id"]
        if sample_id in seen_ids:
            rejects.append({"line": line_no, "reason": "duplicate_sample_id"})
            continue
        seen_ids.add(sample_id)
        text = row["text"]
        if row["split"] not in SPLITS:
            rejects.append({"line": line_no, "reason": "invalid_split"})
            continue
        if not row["source_uri"].startswith("https://"):
            rejects.append({"line": line_no, "reason": "source_uri_must_be_https"})
            continue

        normalized_hash = digest(normalize_for_duplicate_check(text).encode("utf-8"))
        if normalized_hash in normalized_hashes:
            duplicate_rows.append(line_no)
        else:
            normalized_hashes[normalized_hash] = line_no
        patterns = {
            "email_like": EMAIL_RE,
            "turkish_id_like_11_digits": TR_ID_RE,
            "turkish_mobile_phone_like": PHONE_RE,
            "credential_or_secret_assignment": URL_AUTH_RE,
        }
        flags = [name for name, pattern in patterns.items() if pattern.search(text)]
        for flag in flags:
            pii_counts[flag] += 1
        groups_to_splits[row["document_group"]].add(row["split"])
        split_counts[row["split"]] += 1
        records.append({
            "line": line_no,
            "sample_id": sample_id,
            "text_sha256": digest(text.encode("utf-8")),
            "document_group": row["document_group"],
            "source_id": row["source_id"],
            "split": row["split"],
            "human_review": row["human_review"],
            "pii_status": row["pii_status"],
            "pii_indicators": flags,
            "duplicate_normalized_text": normalized_hash in normalized_hashes and normalized_hashes[normalized_hash] != line_no,
        })

    leaking_groups = sorted(group for group, assigned in groups_to_splits.items() if len(assigned) > 1)
    review_not_approved = sum(1 for row in records if row["human_review"] != "approved")
    pii_not_cleared = sum(1 for row in records if row["pii_status"] != "cleared")
    rows_with_pii_indicators = sum(1 for row in records if row["pii_indicators"])
    missing_splits = sorted(SPLITS - set(split_counts))
    report = {
        "schema_version": 1,
        "input_file": args.input.name,
        "input_file_sha256": digest(raw),
        "input_bytes": len(raw),
        "records_parsed": len(records),
        "records_rejected": len(rejects),
        "split_counts": dict(split_counts),
        "unique_document_groups": len(groups_to_splits),
        "duplicate_normalized_text_count": len(duplicate_rows),
        "duplicate_line_numbers": duplicate_rows,
        "pii_indicator_counts": dict(pii_counts),
        "records_with_pii_indicators": rows_with_pii_indicators,
        "records_not_human_approved": review_not_approved,
        "records_pii_status_not_cleared": pii_not_cleared,
        "document_groups_crossing_splits": leaking_groups,
        "missing_splits": missing_splits,
        "rejects": rejects,
        "record_audit": records,
        "training_gate": {
            "eligible_for_human_review_only": not rejects and not duplicate_rows and not rows_with_pii_indicators
                and not review_not_approved and not pii_not_cleared and not leaking_groups and not missing_splits,
            "training_authorized": False,
            "reasons": [
                "This report is an automated local screening, not legal approval.",
                "Source-register approval, exact release/license review, and weight-distribution approval remain separate mandatory gates.",
                "PII regexes can miss sensitive content and can also flag harmless text; human review is required.",
            ],
        },
    }
    try:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        print(f"ERROR: refusing to overwrite report: {args.report}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: could not write report: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({key: value for key, value in report.items() if key != "record_audit"}, ensure_ascii=False, indent=2))
    print(f"Audit report written locally: {args.report}")
    print("No corpus content was uploaded or changed; this tool never authorizes training.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
