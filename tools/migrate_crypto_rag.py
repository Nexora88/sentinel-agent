"""Verified, non-destructive migration from an existing Chroma collection.

This utility never deletes or modifies the source collection. It requires the
operator to stop writers, creates and verifies a full directory backup first,
then copies each record into a NEW encrypted SQLite store and verifies count,
document, metadata, and embedding equality after decrypting the destination.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Iterable

from core.crypto_rag import EncryptedVectorStore, key_from_env


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlinks are not permitted in a migration backup: {path}")
        if path.is_file():
            relative = path.relative_to(root).as_posix().encode("utf-8")
            digest.update(len(relative).to_bytes(4, "big"))
            digest.update(relative)
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
    return digest.hexdigest()


def _assert_outside(path: Path, source: Path, label: str) -> None:
    resolved = path.resolve()
    if resolved == source or source in resolved.parents:
        raise ValueError(f"{label} must be outside the source Chroma directory.")


def create_verified_backup(source_dir: Path, backup_dir: Path) -> str:
    source = source_dir.resolve(strict=True)
    if not source.is_dir():
        raise ValueError("Source Chroma path must be a directory.")
    _assert_outside(backup_dir, source, "Backup path")
    if backup_dir.exists():
        raise FileExistsError("Backup destination already exists; refusing to overwrite it.")
    before = _tree_digest(source)
    backup_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, backup_dir, symlinks=False)
    copied = _tree_digest(backup_dir)
    after = _tree_digest(source)
    if before != copied or before != after:
        raise RuntimeError("Backup verification failed or source changed during backup.")
    return copied


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def migrate_collection(collection: Any, destination: EncryptedVectorStore, *, batch_size: int = 128) -> dict[str, Any]:
    """Copy and verify a Chroma-like collection; never delete source records."""
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or not 1 <= batch_size <= 512:
        raise ValueError("batch_size must be between 1 and 512.")
    source_count = int(collection.count())
    if destination.count() != 0:
        raise ValueError("Destination encrypted store must be empty before migration.")
    migrated = 0
    offset = 0
    while offset < source_count:
        batch = collection.get(
            limit=min(batch_size, source_count - offset),
            offset=offset,
            include=["documents", "metadatas", "embeddings"],
        )
        ids = batch.get("ids") or []
        documents = batch.get("documents") or []
        metadatas = batch.get("metadatas") or [{} for _ in ids]
        embeddings = batch.get("embeddings")
        if embeddings is None or not (len(ids) == len(documents) == len(metadatas) == len(embeddings)):
            raise RuntimeError("Source batch is incomplete; migration stopped without deleting source data.")
        for record_id, document, metadata, embedding in zip(ids, documents, metadatas, embeddings):
            if not isinstance(record_id, str) or not isinstance(document, str):
                raise RuntimeError("Source contains a record without a valid ID or text.")
            if not isinstance(metadata, dict):
                raise RuntimeError("Source metadata is not an object.")
            vector = [float(value) for value in embedding]
            destination.upsert(
                record_id=record_id,
                embedding=vector,
                document=document,
                metadata=metadata,
            )
            verified = destination.get(record_id)
            if verified is None:
                raise RuntimeError(f"Destination record {record_id!r} could not be read back.")
            if (
                verified["document"] != document
                or _canonical(verified["metadata"]) != _canonical(metadata)
                or _canonical(verified["embedding"]) != _canonical(vector)
            ):
                raise RuntimeError(f"Integrity mismatch for record {record_id!r}; source was retained.")
            migrated += 1
        offset += len(ids)
        if not ids and offset < source_count:
            raise RuntimeError("Source returned an empty page before the expected end.")
    if migrated != source_count or destination.count() != source_count or int(collection.count()) != source_count:
        raise RuntimeError("Source/destination record counts differ; source was retained.")
    return {
        "source_records": source_count,
        "destination_records": destination.count(),
        "verified_records": migrated,
        "source_deleted": False,
        "backup_digest_sha256": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path, help="Existing Chroma persistence directory")
    parser.add_argument("--collection", required=True, help="Exact existing Chroma collection name")
    parser.add_argument("--destination", required=True, type=Path, help="NEW encrypted SQLite file path")
    parser.add_argument("--backup-dir", required=True, type=Path, help="NEW backup directory; must not already exist")
    parser.add_argument("--source-quiesced", action="store_true", help="Confirm all writers to the source store are stopped")
    parser.add_argument("--key-env", default="MKAOS_CRYPTO_RAG_KEY", help="Environment variable holding Base64-encoded 32-byte key")
    args = parser.parse_args()

    source = args.source_dir.resolve(strict=True)
    if not args.source_quiesced:
        parser.error("Refusing to migrate unless --source-quiesced is supplied after stopping all writers.")
    _assert_outside(args.destination, source, "Destination")
    if args.destination.exists():
        parser.error("Destination already exists; choose a new empty path to avoid overwriting data.")
    backup_digest = create_verified_backup(source, args.backup_dir)
    print(json.dumps({"backup_verified": True, "backup_digest_sha256": backup_digest}, indent=2))

    import chromadb

    client = chromadb.PersistentClient(path=str(source))
    collection = client.get_collection(args.collection)
    store = EncryptedVectorStore(args.destination, key_from_env(args.key_env))
    report = migrate_collection(collection, store)
    report["backup_digest_sha256"] = backup_digest
    report["backup_path"] = str(args.backup_dir)
    report["destination_path"] = str(args.destination)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
