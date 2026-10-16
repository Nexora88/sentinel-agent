#!/usr/bin/env python3
"""Validate provenance and split hygiene for a proposed MKAOS training corpus.

Metadata checks only; human/legal review is still required.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_SPLITS = {"train", "validation", "test"}
ALLOWED_CONSENT = {"granted", "public_domain", "open_license", "not_required"}


def validate_manifest(manifest: Any, experimental_local_only: bool = False) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["Manifest root must be a JSON object."]
    if manifest.get("schema_version") != 1:
        errors.append("schema_version must equal 1.")
    for key in ("dataset_id", "revision", "created_at", "curator"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            errors.append(f"{key} must be a non-empty string.")
    if manifest.get("license_reviewed") is not True:
        if not (
            experimental_local_only
            and manifest.get("data_rights_mode") == "owner_supplied_local_nonredistributable"
            and manifest.get("source_kind") == "owner_created_or_rights_cleared_local"
        ):
            errors.append("license_reviewed must be true after documented human/legal review.")
    records = manifest.get("records")
    if not isinstance(records, list) or not records:
        return errors + ["records must be a non-empty array of sample provenance records."]
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    counts = {split: 0 for split in ALLOWED_SPLITS}
    required = ("sample_id", "source_id", "source_uri", "license_id", "consent",
                "sha256", "language", "topic", "human_review", "pii_status", "split")
    for index, row in enumerate(records):
        where = f"records[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{where} must be an object.")
            continue
        for key in required:
            if not isinstance(row.get(key), str) or not row[key].strip():
                errors.append(f"{where}.{key} must be a non-empty string.")
        sample_id = row.get("sample_id")
        if isinstance(sample_id, str) and sample_id:
            if sample_id in seen_ids:
                errors.append(f"{where}.sample_id duplicates {sample_id!r}.")
            seen_ids.add(sample_id)
        digest = row.get("sha256")
        if isinstance(digest, str) and digest:
            if not SHA256_RE.fullmatch(digest):
                errors.append(f"{where}.sha256 must be a lowercase 64-character SHA-256 hex digest.")
            elif digest in seen_hashes:
                errors.append(f"{where}.sha256 duplicates content; deduplicate before training.")
            seen_hashes.add(digest)
        uri = row.get("source_uri")
        local_owner_source = (
            experimental_local_only
            and manifest.get("data_rights_mode") == "owner_supplied_local_nonredistributable"
            and manifest.get("source_kind") == "owner_created_or_rights_cleared_local"
        )
        if isinstance(uri, str) and not (
            uri.startswith("https://") or (local_owner_source and uri.startswith("local://"))
        ):
            errors.append(
                f"{where}.source_uri must be HTTPS, or local:// in explicit owner-local experimental mode."
            )
        if row.get("language") != "tr":
            errors.append(f"{where}.language must be 'tr' for the Turkish corpus.")
        if row.get("consent") not in ALLOWED_CONSENT:
            errors.append(f"{where}.consent must document a recognized permission basis.")
        if row.get("human_review") != "approved":
            errors.append(f"{where}.human_review must be 'approved'; pending/rejected data is blocked.")
        if row.get("pii_status") != "cleared":
            errors.append(f"{where}.pii_status must be 'cleared'; unknown/PII data is blocked.")
        if row.get("split") not in ALLOWED_SPLITS:
            errors.append(f"{where}.split must be train, validation, or test.")
        else:
            counts[row["split"]] += 1
        if isinstance(row.get("license_id"), str) and row["license_id"].strip().casefold() in {"unknown", "tbd", "unreviewed"}:
            errors.append(f"{where}.license_id cannot be unknown/unreviewed.")
    missing = [split for split, count in counts.items() if count == 0]
    if missing:
        errors.append("Corpus needs non-empty train/validation/test splits; missing: " + ", ".join(missing) + ".")
    if errors:
        return errors
    if experimental_local_only:
        return ["Metadata checks passed. Experimental local-only mode is NOT legal clearance, dataset quality approval, or model-quality evidence; do not distribute the checkpoint."]
    return ["Metadata checks passed. This is NOT legal clearance, dataset quality approval, or model-quality evidence."]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON provenance manifest")
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read manifest: {exc}", file=sys.stderr)
        return 2
    messages = validate_manifest(manifest)
    failed = any(not message.startswith("Metadata checks passed") for message in messages)
    for message in messages:
        print(("WARNING: " if message.startswith("Metadata checks passed") else "ERROR: ") + message)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
