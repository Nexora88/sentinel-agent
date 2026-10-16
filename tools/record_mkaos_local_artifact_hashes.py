#!/usr/bin/env python3
"""Record SHA-256 and size for locally acquired MKAOS archive/TSV; never uploads files."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys


def digest_file(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"Not a regular file: {path.name}")
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            h.update(chunk)
    return {"filename": path.name, "size_bytes": size, "sha256": h.hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path, help="Locally acquired original archive")
    parser.add_argument("--tsv", required=True, type=Path, help="Exact selected TSV used for extraction")
    parser.add_argument("--output", required=True, type=Path, help="New local JSON record; will not overwrite")
    args = parser.parse_args()
    try:
        archive = args.archive.resolve(strict=True)
        tsv = args.tsv.resolve(strict=True)
        output = args.output.resolve()
        if archive == tsv or archive == output or tsv == output:
            raise ValueError("Archive, TSV and output must be three different files")
        if output.exists():
            raise FileExistsError("Output exists; choose a new filename to preserve the audit trail")
        record = {
            "schema_version": 1,
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "hash_algorithm": "SHA-256",
            "archive": digest_file(archive),
            "selected_tsv": digest_file(tsv),
            "raw_files_uploaded": False,
            "legal_or_training_approval": False,
            "note": "Hashes identify local bytes only; they do not establish provenance, permission, privacy clearance, or model-weight distribution rights."
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except (OSError, ValueError) as exc:
        print(f"Hash record blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(record, ensure_ascii=False, indent=2))
    print(f"Local hash record saved: {output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
