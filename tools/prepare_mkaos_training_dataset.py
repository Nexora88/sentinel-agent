"""Offline CLI for creating an auditable MKAOS supervised-data manifest.

This tool validates metadata and writes a training manifest only when all three
source-level splits contain the configured minimum number of examples. It does
not download data, detect all PII, adjudicate legal rights, or train weights.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from core.model_development import curate_dataset


def prepare_jsonl(lines: list[str], *, min_examples_per_split: int = 1) -> dict[str, Any]:
    if min_examples_per_split < 1:
        raise ValueError("min_examples_per_split must be >= 1")

    records: list[dict[str, Any]] = []
    parse_rejections: list[dict[str, str]] = []
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            parse_rejections.append({"index": str(index), "reason": "invalid_json"})
            continue
        if not isinstance(value, dict):
            parse_rejections.append({"index": str(index), "reason": "record_must_be_json_object"})
            continue
        records.append(value)

    curated = curate_dataset(records)
    curated["rejections"] = parse_rejections + curated["rejections"]
    counts = Counter(item["split"] for item in curated["records"])
    required = {"train", "validation", "test"}
    missing_or_small = {
        split: counts.get(split, 0)
        for split in sorted(required)
        if counts.get(split, 0) < min_examples_per_split
    }
    curated["summary"]["split_counts"] = dict(counts)
    curated["summary"]["minimum_examples_per_split"] = min_examples_per_split
    curated["summary"]["split_gate_failures"] = missing_or_small
    curated["training_allowed"] = not missing_or_small and bool(curated["records"])
    return curated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="UTF-8 JSONL with provenance/licence/consent fields")
    parser.add_argument("--output", required=True, type=Path, help="New output manifest path; existing files are never overwritten")
    parser.add_argument("--report", type=Path, help="Optional JSON quality report path; existing files are never overwritten")
    parser.add_argument("--min-examples-per-split", type=int, default=1)
    args = parser.parse_args(argv)

    try:
        lines = args.input.read_text(encoding="utf-8").splitlines()
        result = prepare_jsonl(lines, min_examples_per_split=args.min_examples_per_split)
    except (OSError, ValueError) as exc:
        print(f"Dataset preparation failed: {exc}", file=sys.stderr)
        return 2

    report = {
        "schema_version": result["schema_version"],
        "summary": result["summary"],
        "rejections": result["rejections"],
        "training_allowed": result["training_allowed"],
        "weights_trained": False,
        "network_used": False,
    }

    if args.report:
        try:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open("x", encoding="utf-8") as handle:
                json.dump(report, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
        except FileExistsError:
            print(f"Refusing to overwrite report: {args.report}", file=sys.stderr)
            return 2
        except OSError as exc:
            print(f"Could not write report: {exc}", file=sys.stderr)
            return 2

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not result["training_allowed"]:
        print("Training manifest blocked: at least one source-level split is too small.", file=sys.stderr)
        return 2

    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError:
        print(f"Refusing to overwrite manifest: {args.output}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Could not write manifest: {exc}", file=sys.stderr)
        return 2

    print(f"Validated manifest written: {args.output}")
    print("No model weights were trained or changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
