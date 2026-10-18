#!/usr/bin/env python3
"""Fail-closed validator for the MKAOS dataset/source review register.

This checks record completeness and internal consistency only; it is not a
legal opinion and cannot verify that cited evidence is truthful.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

FIELDS = (
    "source_id", "source_uri", "source_type", "version_or_snapshot",
    "acquired_at_utc", "license_id", "license_evidence_uri",
    "attribution_requirement", "attribution_evidence_uri", "privacy_evidence_uri",
    "training_permission", "redistribution_permission", "privacy_review",
    "reviewer_id", "review_date", "decision", "notes",
)
PERMISSIONS = {"yes", "no", "unknown"}
PRIVACY = {"passed", "blocked", "not-reviewed"}
ATTRIBUTION = {"required", "not-required", "unknown"}
DECISIONS = {"approved", "quarantine", "rejected"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _valid_date(value: str, *, datetime_utc: bool = False) -> bool:
    try:
        if datetime_utc:
            from datetime import datetime
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.tzinfo is not None and parsed.utcoffset() is not None
        date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def _valid_uri(value: str) -> bool:
    parsed = urlparse(value)
    return (parsed.scheme in {"https", "http"} and bool(parsed.netloc)) or value.startswith("local-archive://")


def validate_register(path: Path) -> tuple[list[str], int, int]:
    errors: list[str] = []
    rows: list[dict[str, str]] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if tuple(reader.fieldnames or ()) != FIELDS:
                return [f"TSV header/schema mismatch; expected: {' | '.join(FIELDS)}"], 0, 0
            for line, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    errors.append(f"line {line}: malformed TSV column count")
                    continue
                row = {key: value.strip() for key, value in row.items()}
                if not any(row.values()):
                    continue
                rows.append(row)
                prefix = f"line {line} ({row.get('source_id') or 'no source_id'})"
                for field in FIELDS[:-1]:
                    if not row[field]:
                        errors.append(f"{prefix}: missing {field}")
                if row["source_id"] and any(old["source_id"] == row["source_id"] for old in rows[:-1]):
                    errors.append(f"{prefix}: duplicate source_id")
                if row["source_uri"] and not _valid_uri(row["source_uri"]):
                    errors.append(f"{prefix}: source_uri must be http(s):// or local-archive://")
                if row["license_evidence_uri"] and not _valid_uri(row["license_evidence_uri"]):
                    errors.append(f"{prefix}: license_evidence_uri must point to evidence using http(s):// or local-archive://")
                for evidence_field in ("attribution_evidence_uri", "privacy_evidence_uri"):
                    if row[evidence_field] and not _valid_uri(row[evidence_field]):
                        errors.append(f"{prefix}: {evidence_field} must point to evidence using http(s):// or local-archive://")
                if row["training_permission"] not in PERMISSIONS:
                    errors.append(f"{prefix}: invalid training_permission")
                if row["redistribution_permission"] not in PERMISSIONS:
                    errors.append(f"{prefix}: invalid redistribution_permission")
                if row["privacy_review"] not in PRIVACY:
                    errors.append(f"{prefix}: invalid privacy_review")
                if row["attribution_requirement"] not in ATTRIBUTION:
                    errors.append(f"{prefix}: invalid attribution_requirement")
                if row["decision"] not in DECISIONS:
                    errors.append(f"{prefix}: invalid decision")
                if row["acquired_at_utc"] and not _valid_date(row["acquired_at_utc"], datetime_utc=True):
                    errors.append(f"{prefix}: acquired_at_utc must be ISO-8601 with timezone")
                if row["review_date"] and not _valid_date(row["review_date"]):
                    errors.append(f"{prefix}: review_date must be YYYY-MM-DD")
                if row["decision"] == "approved":
                    if row["training_permission"] != "yes":
                        errors.append(f"{prefix}: approved source requires training_permission=yes")
                    if row["privacy_review"] != "passed":
                        errors.append(f"{prefix}: approved source requires privacy_review=passed")
                    if row["license_id"].upper() in {"UNKNOWN", "TBD", "N/A"}:
                        errors.append(f"{prefix}: approved source requires a reviewed license_id")
                    if not row["license_evidence_uri"]:
                        errors.append(f"{prefix}: approved source requires license evidence")
                    if row["attribution_requirement"] == "unknown":
                        errors.append(f"{prefix}: approved source requires an attribution decision")
                    if not row["attribution_evidence_uri"]:
                        errors.append(f"{prefix}: approved source requires attribution evidence or a documented not-required decision")
                    if not row["privacy_evidence_uri"]:
                        errors.append(f"{prefix}: approved source requires privacy review evidence")
                    if not row["reviewer_id"] or not row["review_date"]:
                        errors.append(f"{prefix}: approved source requires human reviewer and review date")
    except (OSError, UnicodeError, csv.Error) as exc:
        return [f"cannot read register: {exc}"], 0, 0
    approved = sum(row.get("decision") == "approved" for row in rows)
    return errors, len(rows), approved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", type=Path, default=Path("data/mkaos-source-register.template.tsv"))
    parser.add_argument("--require-approved", action="store_true", help="fail if no reviewed source is approved")
    args = parser.parse_args(argv)
    errors, count, approved = validate_register(args.register)
    if errors:
        print("SOURCE_REGISTER_INVALID")
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    print(f"SOURCE_REGISTER_VALID records={count} approved={approved}")
    if approved == 0:
        print("TRAINING_BLOCKED: no approved source records; this is expected for the empty template.")
        return 2 if args.require_approved else 0
    print("NOTE: validation checks completeness only; humans must verify licence evidence, provenance, and privacy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

