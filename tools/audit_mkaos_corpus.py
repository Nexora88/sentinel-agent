#!/usr/bin/env python3
"""Audit a local MKAOS JSONL corpus against its provenance manifest.

Reports byte-token volume, exact/normalized duplicates, split leakage, provenance
and licensing metadata errors. It never uploads corpus text or prints sample text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from tools.validate_mkaos_training_manifest import validate_manifest


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalized_digest(text: str) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", text).casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def audit(corpus_path: Path, manifest_path: Path, experimental_local_only: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_errors = [
        message for message in validate_manifest(manifest, experimental_local_only)
        if not message.startswith("Metadata checks passed")
    ]
    provenance = {r.get("sample_id"): r for r in manifest.get("records", []) if isinstance(r, dict)}
    samples: dict[str, str] = {}
    exact_hashes: dict[str, str] = {}
    normalized_hashes: dict[str, str] = {}
    split_by_normalized: dict[str, set[str]] = {}
    split_counts: Counter[str] = Counter()
    split_bytes: Counter[str] = Counter()
    duplicate_exact = 0
    duplicate_normalized = 0
    split_leaks = 0
    errors: list[str] = list(manifest_errors)
    total_bytes = 0
    total_records = 0
    malformed = 0
    unique_byte_values: set[int] = set()

    with corpus_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            total_records += 1
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                errors.append(f"line {line_no}: invalid JSON")
                continue
            if not isinstance(item, dict) or not isinstance(item.get("sample_id"), str) or not isinstance(item.get("text"), str) or not item["text"]:
                malformed += 1
                errors.append(f"line {line_no}: expected non-empty sample_id and text strings")
                continue
            sample_id, text = item["sample_id"], item["text"]
            if sample_id in samples:
                errors.append(f"line {line_no}: duplicate sample_id")
                continue
            samples[sample_id] = text
            raw = text.encode("utf-8")
            total_bytes += len(raw)
            unique_byte_values.update(raw)
            row = provenance.get(sample_id)
            if row is None:
                errors.append(f"sample {sample_id!r}: missing from manifest")
                continue
            actual = hashlib.sha256(raw).hexdigest()
            if row.get("sha256") != actual:
                errors.append(f"sample {sample_id!r}: manifest text SHA-256 mismatch")
            split = row.get("split", "unknown")
            split_counts[split] += 1
            split_bytes[split] += len(raw) + 1  # byte tokenizer plus EOS
            if actual in exact_hashes:
                duplicate_exact += 1
                errors.append(f"sample {sample_id!r}: exact duplicate of {exact_hashes[actual]!r}")
            else:
                exact_hashes[actual] = sample_id
            norm = normalized_digest(text)
            if norm in normalized_hashes:
                duplicate_normalized += 1
                prior = normalized_hashes[norm]
                prior_split = provenance.get(prior, {}).get("split")
                if prior_split != split:
                    split_leaks += 1
                    errors.append(f"sample {sample_id!r}: normalized duplicate crosses dataset splits")
                else:
                    errors.append(f"sample {sample_id!r}: normalized near-duplicate of {prior!r}")
            else:
                normalized_hashes[norm] = sample_id
            split_by_normalized.setdefault(norm, set()).add(split)

    missing = set(provenance) - set(samples)
    for sample_id in sorted(missing)[:20]:
        errors.append(f"manifest sample {sample_id!r}: missing from corpus")
    if len(missing) > 20:
        errors.append(f"{len(missing) - 20} additional manifest samples missing from corpus")
    for split in ("train", "validation", "test"):
        if split_counts[split] == 0:
            errors.append(f"corpus has no records in {split} split")

    elapsed = max(time.perf_counter() - started, 1e-9)
    return {
        "schema_version": 1,
        "corpus_file": corpus_path.name,
        "manifest_file": manifest_path.name,
        "records_seen": total_records,
        "valid_records": len(samples),
        "malformed_records": malformed,
        "exact_duplicate_records": duplicate_exact,
        "normalized_duplicate_records": duplicate_normalized,
        "cross_split_normalized_leaks": split_leaks,
        "utf8_text_bytes": total_bytes,
        "byte_tokens_including_eos_estimate": sum(split_bytes.values()),
        "distinct_byte_values_seen": len(unique_byte_values),
        "split_record_counts": dict(split_counts),
        "split_byte_tokens_including_eos_estimate": dict(split_bytes),
        "manifest_record_count": len(provenance),
        "manifest_errors": manifest_errors,
        "errors": errors,
        "elapsed_seconds": round(elapsed, 6),
        "records_per_second": round(total_records / elapsed, 2),
        "byte_tokens_per_second_estimate": round(sum(split_bytes.values()) / elapsed, 2),
        "quality_gate": "pass" if not errors else "fail",
        "limitations": [
            "Byte-token estimates use UTF-8 bytes plus one EOS per record, not model training throughput.",
            "Normalized duplicate detection is a heuristic and does not detect semantic paraphrases.",
            "Metadata checks are not legal advice; humans must verify source rights, licenses, privacy, and redistribution terms.",
            "A passing audit does not establish model quality or Turkish coding/cybersecurity competence."
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    parser.add_argument("--experimental-local-only", action="store_true")
    args = parser.parse_args()
    try:
        report = audit(args.corpus, args.manifest, args.experimental_local_only)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: audit could not complete: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["quality_gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
