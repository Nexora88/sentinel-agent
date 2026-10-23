#!/usr/bin/env python3
"""Provision and verify MKAOS's local BGE-M3 embedding model.

Downloads only when explicitly invoked. Normal application startup must use the
local directory and never fall back to a remote model identifier.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

MODEL_ID = "BAAI/bge-m3"
# Resolve this known upstream revision to a full commit SHA before downloading.
UPSTREAM_REVISION = "5617a9f"
MANIFEST_NAME = ".mkaos-model-sha256.json"
CACHE_DIR_NAME = ".cache"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory(root: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == MANIFEST_NAME or rel.startswith(f"{CACHE_DIR_NAME}/"):
            continue
        if path.is_symlink():
            raise RuntimeError(f"Symlink is not allowed in model directory: {rel}")
        entries[rel] = sha256_file(path)
    if not entries:
        raise RuntimeError(f"No model files found in {root}")
    return entries


def write_manifest(root: Path, resolved_revision: str) -> Path:
    manifest = {
        "schema_version": 1,
        "model_id": MODEL_ID,
        "resolved_revision": resolved_revision,
        "hash_algorithm": "sha256",
        "files": inventory(root),
        "note": "Generated from files actually present after download; do not hand-edit.",
    }
    path = root / MANIFEST_NAME
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def verify(root: Path) -> None:
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise RuntimeError(f"Missing hash inventory: {manifest_path}. Run provisioning first.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("model_id") != MODEL_ID or manifest.get("hash_algorithm") != "sha256":
        raise RuntimeError("Model inventory identity or hash algorithm is invalid.")
    expected = manifest.get("files")
    if not isinstance(expected, dict) or not expected:
        raise RuntimeError("Model inventory has no file hashes.")
    actual = inventory(root)
    if actual.keys() != expected.keys():
        missing = sorted(expected.keys() - actual.keys())
        unexpected = sorted(actual.keys() - expected.keys())
        raise RuntimeError(f"Model file set changed; missing={missing[:10]}, unexpected={unexpected[:10]}")
    changed = [name for name, digest in expected.items() if actual[name] != digest]
    if changed:
        raise RuntimeError(f"SHA-256 mismatch for: {', '.join(changed[:20])}")
    print(f"OK: verified {len(actual)} model files; revision {manifest.get('resolved_revision')}")


def provision(root: Path, skip_smoke_test: bool) -> None:
    try:
        from huggingface_hub import HfApi, snapshot_download
    except ImportError as exc:
        raise RuntimeError("Install scripts/rag-model-requirements.txt first.") from exc

    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise RuntimeError(
            f"Refusing to overwrite non-empty model directory: {root}. "
            "Choose an empty directory or move the existing files aside."
        )

    api = HfApi()
    info = api.model_info(MODEL_ID, revision=UPSTREAM_REVISION)
    resolved_revision = info.sha
    if not resolved_revision or len(resolved_revision) != 40:
        raise RuntimeError("Could not resolve upstream model revision to a full commit SHA.")

    print(f"Downloading {MODEL_ID}@{resolved_revision} to {root}")
    print("The model is several GB; ensure sufficient disk space and a trusted network.")
    snapshot_download(
        repo_id=MODEL_ID,
        revision=resolved_revision,
        local_dir=str(root),
        repo_type="model",
    )

    if not skip_smoke_test:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("Install scripts/rag-model-requirements.txt first.") from exc
        model = SentenceTransformer(
            str(root),
            local_files_only=True,
            trust_remote_code=False,
        )
        vectors = model.encode(
            ["MKAOS yerel semantik arama doğrulaması.", "Türkiye'de yerel yapay zekâ."],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        if len(vectors) != 2 or vectors.shape[-1] != 1024:
            raise RuntimeError(f"Unexpected BGE-M3 embedding shape: {getattr(vectors, 'shape', None)}")
        print(f"Smoke test passed: embedding shape {vectors.shape}")

    manifest_path = write_manifest(root, resolved_revision)
    verify(root)
    print(f"Created SHA-256 inventory: {manifest_path}")
    print("Provisioning complete. Keep this directory local; do not commit model weights.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=Path("var/models/bge-m3"))
    parser.add_argument("--verify", action="store_true", help="verify existing files offline; never download")
    parser.add_argument("--skip-smoke-test", action="store_true", help="skip local embedding inference check")
    args = parser.parse_args()
    root = args.model_dir.expanduser().resolve()
    try:
        if args.verify:
            verify(root)
        else:
            provision(root, args.skip_smoke_test)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
