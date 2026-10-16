#!/usr/bin/env python3
"""Build trainer-compatible local files from a human-reviewed MKAOS JSONL corpus.

Offline only. Never downloads data or uploads corpus contents. This tool does
not approve a source: the source-register gate remains authoritative.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

SPLITS = {"train", "validation", "test"}
REQUIRED = (
    "sample_id", "text", "source_id", "source_uri", "document_group",
    "license_id", "consent", "language", "topic", "split",
    "human_review", "pii_status",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def build(lines: list[str], *, dataset_id: str, revision: str, curator: str,
          license_reviewed: bool) -> tuple[list[dict[str, str]], dict[str, Any], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    hashes: set[str] = set()
    group_splits: dict[str, set[str]] = defaultdict(set)
    source_splits: dict[str, set[str]] = defaultdict(set)
    errors: list[str] = []
    for lineno, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"line {lineno}: invalid JSON")
            continue
        if not isinstance(row, dict):
            errors.append(f"line {lineno}: record must be an object")
            continue
        missing = [key for key in REQUIRED if not isinstance(row.get(key), str) or not row[key].strip()]
        if missing:
            errors.append(f"line {lineno}: missing/empty fields: {', '.join(missing)}")
            continue
        sid, text = row["sample_id"], row["text"]
        if sid in ids:
            errors.append(f"line {lineno}: duplicate sample_id")
        ids.add(sid)
        normalized_hash = digest(normalize(text))
        if normalized_hash in hashes:
            errors.append(f"line {lineno}: normalized duplicate text")
        hashes.add(normalized_hash)
        if row["language"] != "tr":
            errors.append(f"line {lineno}: language must be tr")
        if row["split"] not in SPLITS:
            errors.append(f"line {lineno}: invalid split")
        if row["human_review"] != "approved":
            errors.append(f"line {lineno}: human_review must be approved")
        if row["pii_status"] != "cleared":
            errors.append(f"line {lineno}: pii_status must be cleared")
        if row["consent"] not in {"granted", "public_domain", "open_license", "not_required"}:
            errors.append(f"line {lineno}: consent/permission basis is not recognized")
        if not row["source_uri"].startswith("https://"):
            errors.append(f"line {lineno}: source_uri must use HTTPS")
        if row["license_id"].casefold() in {"unknown", "tbd", "unreviewed"}:
            errors.append(f"line {lineno}: license_id is not reviewed")
        group_splits[row["document_group"]].add(row["split"])
        source_splits[row["source_id"]].add(row["split"])
        rows.append(row)
    if not rows:
        errors.append("no usable records")
    for group, splits in group_splits.items():
        if len(splits) > 1:
            errors.append(f"document group crosses splits: {group}")
    if errors:
        raise ValueError("\n".join(errors[:100]))
    counts = {split: sum(row["split"] == split for row in rows) for split in sorted(SPLITS)}
    if any(counts[split] == 0 for split in SPLITS):
        raise ValueError("train, validation and test must all be non-empty")
    corpus = [{"sample_id": row["sample_id"], "text": row["text"]} for row in rows]
    manifest = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "revision": revision,
        "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "curator": curator,
        "license_reviewed": license_reviewed,
        "records": [
            {
                "sample_id": row["sample_id"],
                "source_id": row["source_id"],
                "source_uri": row["source_uri"],
                "license_id": row["license_id"],
                "consent": row["consent"],
                "sha256": digest(row["text"]),
                "language": row["language"],
                "topic": row["topic"],
                "human_review": row["human_review"],
                "pii_status": row["pii_status"],
                "split": row["split"],
            }
            for row in rows
        ],
    }
    report = {
        "records": len(rows),
        "split_counts": counts,
        "document_groups": len(group_splits),
        "sources": len(source_splits),
        "source_disjoint": all(len(splits) == 1 for splits in source_splits.values()),
        "document_group_disjoint": True,
        "license_reviewed_flag": license_reviewed,
        "raw_text_in_report": False,
        "training_started": False,
        "note": "Source-register approval is checked separately by the trainer. A true license_reviewed flag records curator attestation; it is not independent legal advice.",
    }
    return corpus, manifest, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Human-reviewed local JSONL; never committed")
    parser.add_argument("--corpus-output", required=True, type=Path, help="New trainer JSONL output")
    parser.add_argument("--manifest-output", required=True, type=Path, help="New provenance manifest output")
    parser.add_argument("--report-output", required=True, type=Path, help="New privacy-safe report output")
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--revision", required=True, help="Exact source release and local input SHA-256 reference")
    parser.add_argument("--curator", required=True, help="Responsible human reviewer")
    parser.add_argument("--confirm-human-license-review", action="store_true",
                        help="Attest that exact release/file license and weight-distribution terms were reviewed")
    args = parser.parse_args()
    try:
        raw = args.input.read_bytes()
        input_hash = hashlib.sha256(raw).hexdigest()
        lines = raw.decode("utf-8-sig").splitlines()
        corpus, manifest, report = build(
            lines, dataset_id=args.dataset_id, revision=args.revision,
            curator=args.curator, license_reviewed=args.confirm_human_license_review,
        )
        report["input_sha256"] = input_hash
        outputs = [
            (args.corpus_output, lambda f: [f.write(json.dumps(row, ensure_ascii=False) + "\n") for row in corpus]),
            (args.manifest_output, lambda f: json.dump(manifest, f, ensure_ascii=False, indent=2)),
            (args.report_output, lambda f: json.dump(report, f, ensure_ascii=False, indent=2)),
        ]
        for path, writer in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="") as handle:
                writer(handle)
                handle.write("\n")
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Corpus manifest build blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("Manifest files written locally. Training is still blocked unless the source register independently approves every source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
