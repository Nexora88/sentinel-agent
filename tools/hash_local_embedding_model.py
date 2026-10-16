#!/usr/bin/env python3
"""Create or verify a SHA-256 inventory for an already-installed local embedding model.

This tool never downloads, modifies, or approves model weights. The inventory
is evidence of file identity only; license/privacy approval is a separate review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def inventory_model(model_dir: Path) -> dict[str, Any]:
    root = model_dir.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Model path must be an existing directory.")
    files: dict[str, dict[str, Any]] = {}
    for current, dirs, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        for dirname in list(dirs):
            path = current_path / dirname
            if path.is_symlink():
                raise ValueError(f"Symlinked model directories are not allowed: {path.relative_to(root)}")
        for name in names:
            path = current_path / name
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"Model inventory only accepts regular files: {path.relative_to(root)}")
            relative = path.relative_to(root).as_posix()
            digest, size = sha256_file(path)
            files[relative] = {"sha256": digest, "size_bytes": size}
    if not files:
        raise ValueError("Model directory contains no regular files.")
    return {
        "schema_version": 1,
        "model_directory_name": root.name,
        "file_count": len(files),
        "total_size_bytes": sum(item["size_bytes"] for item in files.values()),
        "files": dict(sorted(files.items())),
        "review_status": "pending_human_license_privacy_and_quality_review",
        "note": "SHA-256 inventory proves file identity, not license clearance, safety, or semantic quality.",
    }


def verify_inventory(model_dir: Path, manifest: Any) -> list[str]:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return ["Unsupported or invalid model inventory manifest."]
    listed = manifest.get("files")
    if not isinstance(listed, dict) or not listed:
        return ["Manifest files must be a non-empty object."]
    actual = inventory_model(model_dir)
    errors: list[str] = []
    expected_names = set(listed)
    actual_names = set(actual["files"])
    if expected_names != actual_names:
        errors.append(
            "File set mismatch; missing=" + repr(sorted(expected_names - actual_names)[:10])
            + "; extra=" + repr(sorted(actual_names - expected_names)[:10])
        )
    for name in sorted(expected_names & actual_names):
        expected = listed[name]
        got = actual["files"][name]
        if not isinstance(expected, dict):
            errors.append(f"Invalid manifest entry for {name!r}.")
            continue
        if expected.get("sha256") != got["sha256"]:
            errors.append(f"SHA-256 mismatch for {name!r}.")
        if expected.get("size_bytes") != got["size_bytes"]:
            errors.append(f"Size mismatch for {name!r}.")
    if manifest.get("file_count") != actual["file_count"]:
        errors.append("File count mismatch.")
    if manifest.get("total_size_bytes") != actual["total_size_bytes"]:
        errors.append("Total size mismatch.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, type=Path, help="Existing local model directory; never downloaded by this tool")
    parser.add_argument("--output", type=Path, help="Write the inventory outside the model directory")
    parser.add_argument("--verify", type=Path, help="Verify the model directory against an existing JSON inventory")
    args = parser.parse_args()
    try:
        if args.verify:
            manifest = json.loads(args.verify.read_text(encoding="utf-8"))
            errors = verify_inventory(args.model_dir, manifest)
            if errors:
                for error in errors:
                    print("ERROR: " + error, file=sys.stderr)
                return 2
            print("Model file inventory matches: " + str(args.verify))
            print("This does not certify license/privacy approval or embedding quality.")
            return 0
        manifest = inventory_model(args.model_dir)
        rendered = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            output = args.output.expanduser().resolve()
            root = args.model_dir.expanduser().resolve()
            if output == root or root in output.parents:
                raise ValueError("Write the inventory outside the model directory to avoid self-inclusion.")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8")
            print("Wrote local model file inventory: " + str(output))
        else:
            print(rendered, end="")
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
