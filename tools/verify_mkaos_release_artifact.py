#!/usr/bin/env python3
"""Fail-closed verification for a MKAOS release artifact manifest.

This checks byte identity and required provenance metadata. It does NOT verify a
cryptographic signature or certify licenses; those require a separately verified
attestation and human review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def verify(artifact: Path, manifest_path: Path) -> dict[str, str]:
    if not artifact.is_file() or artifact.is_symlink():
        raise ValueError("artifact must be a regular, non-symlink file")
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("manifest must be a regular, non-symlink file")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"manifest is unreadable or invalid JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")

    expected = manifest.get("artifact_sha256")
    commit = manifest.get("source_commit")
    sbom_hash = manifest.get("sbom_sha256")
    if not isinstance(expected, str) or not _SHA256.fullmatch(expected):
        raise ValueError("artifact_sha256 must be a lowercase 64-character SHA-256")
    if not isinstance(commit, str) or not _COMMIT.fullmatch(commit):
        raise ValueError("source_commit must be a full 40-character Git commit SHA")
    if not isinstance(sbom_hash, str) or not _SHA256.fullmatch(sbom_hash):
        raise ValueError("sbom_sha256 must be a lowercase 64-character SHA-256")
    if not isinstance(manifest.get("builder_id"), str) or not manifest["builder_id"].strip():
        raise ValueError("builder_id is required")
    if not isinstance(manifest.get("build_recipe"), str) or not manifest["build_recipe"].strip():
        raise ValueError("build_recipe is required")

    digest = hashlib.sha256()
    with artifact.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected:
        raise ValueError(f"artifact SHA-256 mismatch: expected {expected}, got {actual}")
    return {
        "status": "BYTE_IDENTITY_VERIFIED",
        "artifact_sha256": actual,
        "source_commit": commit,
        "sbom_sha256": sbom_hash,
        "builder_id": manifest["builder_id"],
        "build_recipe": manifest["build_recipe"],
        "signature_verified": "false",
        "license_reviewed": "false",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.artifact, args.manifest)
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "REJECTED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
