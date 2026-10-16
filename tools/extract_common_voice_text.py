#!/usr/bin/env python3
"""Extract local Common Voice Turkish text as UNAPPROVED source-aware candidates.

Offline only: no network, no audio loading, no upload, and no training. The
Common Voice release's CC0 label is not copied blindly to underlying sentence
sources: every source label needs a human/legal review. Source labels are hashed
into IDs for deterministic grouping; original labels are retained for review.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def split_for_source(source_hash: str) -> str:
    # Source-level assignment prevents the same underlying source entering all splits.
    bucket = int(source_hash[:8], 16) % 100
    return "train" if bucket < 80 else ("validation" if bucket < 90 else "test")


def extract(input_tsv: Path, *, release: str, source_uri: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = input_tsv.read_bytes()
    file_hash = sha256(raw)
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Input TSV must be UTF-8.") from exc
    reader = csv.DictReader(decoded.splitlines(), delimiter="\t")
    if not reader.fieldnames or not {"sentence", "source"}.issubset(set(reader.fieldnames)):
        raise ValueError("TSV must contain both 'sentence' and 'source' columns; do not discard source provenance.")

    # Deduplicate normalized text, but preserve all observed source labels for human review.
    by_hash: dict[str, dict[str, Any]] = {}
    empty = 0
    missing_source = 0
    nonempty = 0
    duplicates = 0
    for row in reader:
        sentence = " ".join((row.get("sentence") or "").split())
        source_label = " ".join((row.get("source") or "").split())
        if not sentence:
            empty += 1
            continue
        if not source_label:
            missing_source += 1
            continue
        normalized = normalize(sentence)
        if not normalized:
            empty += 1
            continue
        nonempty += 1
        text_hash = sha256(normalized.encode("utf-8"))
        if text_hash in by_hash:
            duplicates += 1
            labels = by_hash[text_hash]["source_labels"]
            if source_label not in labels:
                labels.append(source_label)
        else:
            source_hash = sha256(source_label.encode("utf-8"))
            by_hash[text_hash] = {
                "sentence": sentence,
                "text_hash": text_hash,
                "source_labels": [source_label],
                "primary_source_hash": source_hash,
            }

    records: list[dict[str, Any]] = []
    for text_hash, item in sorted(by_hash.items()):
        source_hash = item["primary_source_hash"]
        records.append({
            "sample_id": "cv-tr-" + text_hash[:24],
            "text": item["sentence"],
            "source_id": "cv-underlying-source-" + source_hash[:16],
            "source_label": item["source_labels"][0],
            "all_observed_source_labels": sorted(item["source_labels"]),
            "source_uri": source_uri,
            "document_group": "source-" + source_hash[:16],
            "license_id": "unreviewed",
            "consent": "open_license",
            "language": "tr",
            "topic": "unclassified",
            "split": split_for_source(source_hash),
            "human_review": "pending",
            "pii_status": "unknown",
            "release": release,
            "source_file_sha256": file_hash,
            "text_sha256": sha256(item["sentence"].encode("utf-8")),
        })

    counts = {name: sum(row["split"] == name for row in records) for name in ("train", "validation", "test")}
    source_splits: dict[str, set[str]] = defaultdict(set)
    for row in records:
        source_splits[row["source_id"]].add(row["split"])
    report = {
        "schema_version": 2,
        "source_id": "mozilla-common-voice-text",
        "release": release,
        "source_uri": source_uri,
        "input_filename": input_tsv.name,
        "input_file_bytes": len(raw),
        "input_file_sha256": file_hash,
        "unique_normalized_sentences": len(records),
        "empty_rows_skipped": empty,
        "rows_missing_source_skipped": missing_source,
        "nonempty_rows_seen": nonempty,
        "duplicate_normalized_sentences_removed": duplicates,
        "underlying_source_groups": len(source_splits),
        "split_counts": counts,
        "source_disjoint": all(len(value) == 1 for value in source_splits.values()),
        "text_only": True,
        "audio_read_or_copied": False,
        "network_used": False,
        "training_started": False,
        "human_review": "pending",
        "pii_review": "pending",
        "training_allowed": False,
        "limitations": [
            "Underlying source labels are untrusted metadata and require human/legal review; they are not licenses.",
            "license_id is deliberately unreviewed; the general CC0 claim is not assumed to clear every Turkish sentence origin.",
            "Duplicate text from multiple sources retains all observed labels but is assigned by the first observed source hash; review these multi-origin rows before splitting or training.",
            "Source-level hashing can leave one or more splits empty; do not weaken split isolation to force a training run.",
            "Regex and automated screening cannot prove the absence of personal or sensitive information.",
            "The Common Voice package must not be mirrored or redistributed; keep all source data local and use the authorized platform flow.",
        ],
    }
    return records, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-tsv", required=True, type=Path, help="Local Common Voice TSV with sentence and source columns")
    parser.add_argument("--release", required=True, help="Exact release label, e.g. Scripted Speech v27.0 Turkish")
    parser.add_argument("--source-uri", required=True, help="HTTPS URL for the exact dataset/product page")
    parser.add_argument("--output-jsonl", required=True, type=Path, help="New local output path; never overwritten")
    parser.add_argument("--report-json", required=True, type=Path, help="New local report path; never overwritten")
    args = parser.parse_args()
    if not args.release.strip() or not args.source_uri.startswith("https://"):
        parser.error("--release must be exact and --source-uri must be HTTPS")
    try:
        records, report = extract(args.input_tsv, release=args.release.strip(), source_uri=args.source_uri)
        if not records:
            raise ValueError("No usable source-attributed sentences found.")
        if not all(report["split_counts"].values()):
            print("WARNING: source-level isolation left at least one split empty; add independently reviewed sources instead of weakening the split.", file=sys.stderr)
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
    print("Unapproved candidate corpus created locally; source register remains closed and no model was trained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
