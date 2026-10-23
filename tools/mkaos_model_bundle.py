"""Fail-closed integrity checks for local MKAOS model bundles.

This module is deliberately stdlib-only and never downloads models. A bundle
manifest is trusted only after its files, SHA-256 digests, tokenizer contract,
and optional architecture identifier have been checked.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ModelBundleError(ValueError):
    """Raised when a local model bundle cannot be verified safely."""


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_model_bundle(manifest_path: str | Path) -> dict[str, Any]:
    """Verify a local bundle manifest and return a normalized status record.

    Required JSON fields:
      schema_version: 1
      model_file: relative path to checkpoint
      model_sha256: lowercase/uppercase SHA-256 hex
      tokenizer_file: relative path to tokenizer artifact
      tokenizer_sha256: SHA-256 hex
      tokenizer_contract: non-empty identifier
      model_id: non-empty immutable version identifier

    Absolute paths, path traversal, missing files, malformed digests, and
    hash mismatches are rejected. This function does not assert that a runtime
    can load arbitrary architecture formats; that requires a runtime smoke test.
    """
    manifest_path = Path(manifest_path).resolve()
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ModelBundleError(f"Cannot read model manifest: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ModelBundleError("manifest must be a schema_version=1 JSON object")

    required = ("model_id", "model_file", "model_sha256", "tokenizer_file",
                "tokenizer_sha256", "tokenizer_contract")
    missing = [key for key in required if not isinstance(data.get(key), str) or not data[key].strip()]
    if missing:
        raise ModelBundleError("missing or empty manifest fields: " + ", ".join(missing))

    root = manifest_path.parent
    verified: dict[str, str] = {}
    for file_key, hash_key in (("model_file", "model_sha256"),
                               ("tokenizer_file", "tokenizer_sha256")):
        relative = Path(data[file_key])
        if relative.is_absolute() or ".." in relative.parts:
            raise ModelBundleError(f"{file_key} must be a safe relative path")
        target = (root / relative).resolve()
        if target != root and root not in target.parents:
            raise ModelBundleError(f"{file_key} resolves outside the bundle directory")
        if not target.is_file():
            raise ModelBundleError(f"{file_key} does not exist: {relative}")
        expected = data[hash_key].lower()
        if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
            raise ModelBundleError(f"{hash_key} must be a 64-character SHA-256 hex digest")
        actual = sha256_file(target)
        if actual != expected:
            raise ModelBundleError(f"SHA-256 mismatch for {file_key}")
        verified[file_key] = actual

    return {
        "status": "verified",
        "model_id": data["model_id"],
        "tokenizer_contract": data["tokenizer_contract"],
        "model_sha256": verified["model_file"],
        "tokenizer_sha256": verified["tokenizer_file"],
        "manifest_path": str(manifest_path),
        "network_used": False,
        "runtime_load_tested": False,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="path to local model-bundle JSON manifest")
    args = parser.parse_args()
    try:
        status = verify_model_bundle(args.manifest)
    except ModelBundleError as exc:
        parser.exit(2, f"MODEL_BUNDLE_REJECTED: {exc}\n")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
