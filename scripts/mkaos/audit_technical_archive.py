#!/usr/bin/env python3
"""Create a provenance-only report for a downloaded technical dataset archive.

This tool intentionally does not extract source files, load pickle metadata, publish
the archive, or approve the dataset for model training. Per-repository licensing
and redistribution terms require separate human review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--file-list", required=True, type=Path)
    parser.add_argument("--sha-file", required=True, type=Path)
    parser.add_argument("--language", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    archive = args.archive
    if not archive.is_file() or archive.stat().st_size == 0:
        raise SystemExit("Archive is missing or empty")
    entries = [line.strip() for line in args.file_list.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not entries:
        raise SystemExit("Archive listing is empty")
    if any(name.startswith("/") or ".." in Path(name).parts for name in entries):
        raise SystemExit("Unsafe archive path detected in listing")

    sha_line = args.sha_file.read_text(encoding="utf-8").split()[0]
    actual_sha = sha256_file(archive)
    if sha_line != actual_sha:
        raise SystemExit("SHA-256 file does not match downloaded archive")

    report = {
        "schema_version": 1,
        "dataset": "CodeSearchNet",
        "language": args.language,
        "source_url": args.source_url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive": {
            "filename": archive.name,
            "size_bytes": archive.stat().st_size,
            "sha256": actual_sha,
            "zip_entries_count": len(entries),
            "zip_entry_names": entries[:5000],
            "entry_names_truncated": len(entries) > 5000,
        },
        "rights_review": {
            "dataset_license": "Mixed / source-level terms; do not assume one blanket license",
            "per_repository_license_inventory_reviewed": False,
            "privacy_reviewed": False,
            "attribution_and_sharealike_reviewed": False,
            "training_permission_approved": False,
            "checkpoint_redistribution_approved": False,
            "status": "pending_human_review",
        },
        "training_gate": "BLOCKED",
        "important_limitations": [
            "SHA-256 computed during download confirms report consistency, not authenticity against a separately published upstream checksum.",
            "Archive integrity check does not establish legal permission to train or redistribute model weights.",
            "The archive is deliberately not uploaded as an artifact and is deleted at job end.",
            "Do not add this source to the approved-source register until source-level license, provenance, privacy, attribution and model-weight terms are reviewed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote provenance-only audit: {args.output}")
    print(f"Archive SHA-256: {actual_sha}")
    print(f"ZIP entries listed: {len(entries)}")
    print("Training permission: BLOCKED (human rights/privacy review pending)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
