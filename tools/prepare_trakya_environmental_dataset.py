#!/usr/bin/env python3
"""Validate sourced environmental observations and make leakage-resistant splits.

This tool deliberately refuses unapproved sources. It does not download data,
infer labels, or claim a trained model exists.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

REQUIRED_COLUMNS = {"sample_id", "event_id", "timestamp", "latitude", "longitude", "label", "source_id"}
SPLITS = ("train", "validation", "test")


def load_registry(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    sources = payload.get("sources")
    if not isinstance(sources, list):
        raise ValueError("Registry must contain a 'sources' list.")
    result = {}
    for source in sources:
        sid = source.get("source_id")
        if not sid or sid in result:
            raise ValueError("Every source needs a unique non-empty source_id.")
        result[sid] = source
    return result


def validate_row(row: dict, line: int, registry: dict) -> None:
    missing = sorted(REQUIRED_COLUMNS - row.keys())
    if missing:
        raise ValueError(f"Row {line}: missing columns: {', '.join(missing)}")
    for key in ("sample_id", "event_id", "timestamp", "label", "source_id"):
        if not (row.get(key) or "").strip():
            raise ValueError(f"Row {line}: {key} is empty.")
    try:
        lat, lon = float(row["latitude"]), float(row["longitude"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Row {line}: latitude/longitude must be numeric.") from exc
    if not (40.0 <= lat <= 42.5 and 25.0 <= lon <= 29.5):
        raise ValueError(f"Row {line}: coordinates fall outside the configured Trakya bounding box.")
    source = registry.get(row["source_id"])
    if source is None:
        raise ValueError(f"Row {line}: source_id {row['source_id']!r} is not registered.")
    if source.get("approval_status") != "approved":
        raise ValueError(f"Row {line}: source {row['source_id']!r} is not approved; refusing to process.")
    for field in ("license", "source_url", "access_basis", "label_method"):
        if not str(source.get(field, "")).strip():
            raise ValueError(f"Registered source {row['source_id']!r} lacks required {field}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="CSV of labeled observations")
    parser.add_argument("--registry", default=Path("data/trakya/source-register.json"), type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20261020)
    args = parser.parse_args()

    registry = load_registry(args.registry)
    with args.input.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError(f"CSV header must include: {', '.join(sorted(REQUIRED_COLUMNS))}")
        rows = list(reader)
    if not rows:
        raise ValueError("Input dataset is empty.")

    seen = set()
    for line, row in enumerate(rows, start=2):
        validate_row(row, line, registry)
        sid = row["sample_id"]
        if sid in seen:
            raise ValueError(f"Row {line}: duplicate sample_id {sid!r}.")
        seen.add(sid)

    # Split by event_id, never by individual observation: observations from one
    # fire/event cannot leak across train, validation and test.
    groups = {}
    for row in rows:
        groups.setdefault(row["event_id"], []).append(row)
    event_ids = sorted(groups)
    random.Random(args.seed).shuffle(event_ids)
    if len(event_ids) < 3:
        raise ValueError("At least 3 distinct event_id groups are required for train/validation/test.")
    n = len(event_ids)
    n_test = max(1, round(n * 0.2))
    n_val = max(1, round(n * 0.1))
    if n_test + n_val >= n:
        n_test, n_val = 1, 1
    assignments = {}
    for event in event_ids[:n - n_val - n_test]:
        assignments[event] = "train"
    for event in event_ids[n - n_val - n_test:n - n_test]:
        assignments[event] = "validation"
    for event in event_ids[n - n_test:]:
        assignments[event] = "test"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = {"schema_version": 1, "seed": args.seed, "split_unit": "event_id",
               "source_registry_sha256": hashlib.sha256(args.registry.read_bytes()).hexdigest(),
               "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
               "counts": {}, "label_counts": {}, "event_counts": {}}
    for split in SPLITS:
        split_rows = [row for row in rows if assignments[row["event_id"]] == split]
        target = args.output_dir / f"{split}.csv"
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(split_rows)
        summary["counts"][split] = len(split_rows)
        summary["label_counts"][split] = dict(Counter(row["label"] for row in split_rows))
        summary["event_counts"][split] = len({row["event_id"] for row in split_rows})
    summary["split_event_ids"] = {split: sorted(k for k, v in assignments.items() if v == split) for split in SPLITS}
    (args.output_dir / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
