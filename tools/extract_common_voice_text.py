#!/usr/bin/env python3
"""Extract text-only candidate records from a locally obtained Common Voice Turkish TSV.

Offline only: no network, no audio loading, no upload, and no training. The output
is deliberately marked pending/unknown and cannot pass MKAOS's training gates
until a human reviews the exact release, licence, privacy and weight-distribution
conditions and the source register is explicitly approved.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def split_for_group(group_hash: str) -> str:
    # Stable across runs; duplicates are collapsed before assignment.
    bucket = int(group_hash[:8], 16) % 100
    return "train" if bucket < 80 else ("validation" if bucket < 90 else "test")


def extract(input_tsv: Path, *, release: str, source_uri: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = input_tsv.read_bytes()
    file_hash = sha256(raw)
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Input TSV must be UTF-8.") from exc

    reader = csv.DictReader(decoded.splitlines(), delimiter="\t")
    if not reader.fieldnames or "sentence" not in reader.fieldnames:
        raise ValueError("TSV must contain a 'sentence' column (select a text TSV, not an audio file).")

    by_hash: dict[str, str] = {}
    empty = 0
    for line_number, row in enumerate(reader, start=2):
        sentence = " ".join((row.get("sentence") or "").split())
        if not sentence:
            empty += 1
            continue
        normalized = normalize(sentence)
        if not normalized:
            empty += 1
            continue
        digest = sha256(normalized.encode("utf-8"))
        by_hash.setdefault(digest, sentence)

    records: list[dict[str, Any]] = []
    for digest, sentence in sorted(by_hash.items()):
        records.append({
            "sample_id": "cv-tr-" + digest[:24],
            "text": sentence,
            "source_id": "mozilla-common-voice-text",
            "source_uri": source_uri,
            "document_group": "sentence-" + digest,
            "license_id": "CC0-1.0",
            "split": split_for_group(digest),
            "human_review": "pending",
            "pii_status": "unknown",
            "language": "tr",
            "release": release,
            "source_file_sha256": file_hash,
            "text_sha256": sha256(sentence.encode("utf-8")),
        })

    counts = {name: sum(row["split"] == name for row in records) for name in ("train", "validation", "test")}
    report = {
        "schema_version": 1,
        "source_id": "mozilla-common-voice-text",
        "release": release,
        "source_uri": source_uri,
        "input_filename": input_tsv.name,
        "input_file_bytes": len(raw),
        "input_file_sha256": file_hash,
        "unique_normalized_sentences": len(records),
        "empty_rows_skipped": empty,
        "duplicate_normalized_sentences_removed": max(0, sum(1 for _ in []) ),
        "split_counts": counts,
        "text_only": True,
        "audio_read_or_copied": False,
        "network_used": False,
        "training_started": False,
        "human_review": "pending",
        "pii_review": "pending",
        "training_allowed": False,
        "limitations": [
            "This is an extraction and deduplication report, not legal or privacy approval.",
            "All rows share one source_id, so this split is document/sentence-group-disjoint, not source-disjoint.",
            "Sentence-level regex review cannot prove the absence of personal or sensitive information.",
            "Verify the exact release page, Turkish subset terms and redistribution/model-weight conditions before changing any review status.",
        ],
    }
    return records, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-tsv", required=True, type=Path, help="Local Common Voice Turkish TSV with a sentence column")
    parser.add_argument("--release", required=True, help="Exact release label, e.g. Scripted Speech v27.0 Turkish")
    parser.add_argument("--source-uri", required=True, help="HTTPS URL for the exact dataset/product page")
    parser.add_argument("--output-jsonl", required=True, type=Path, help="New local output path; never overwritten")
    parser.add_argument("--report-json", required=True, type=Path, help="New local report path; never overwritten")
    args = parser.parse_args()
    if not args.release.strip() or not args.source_uri.startswith("https://"):
        parser.error("--release must be exact and --source-uri must be HTTPS")
    try:
        records, report = extract(args.input_tsv, release=args.release.strip(), source_uri=args.source_uri)
        if not records or not all(report["split_counts"].values()):
            raise ValueError("Not enough unique sentences to populate all three provisional splits.")
        for path, writer in (
            (args.output_jsonl, lambda handle: [handle.write(json.dumps(row, ensure_ascii=False) + "\n") for row in records]),
            (args.report_json, lambda handle: json.dump(report, handle, ensure_ascii=False, indent=2)),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="") as handle:
                writer(handle)
                handle.write("\n")
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        print(f"Extraction blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("Candidate corpus created locally; source gate remains closed and no model was trained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
