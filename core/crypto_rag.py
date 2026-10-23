"""Opt-in encrypted vector store for sensitive local RAG data.

Only opaque IDs, nonces and AES-GCM ciphertext are stored in SQLite. Embeddings,
source text and metadata are encrypted together. This is not a drop-in Chroma
replacement; callers must explicitly opt into this store.
"""
from __future__ import annotations
import base64, json, math, os, secrets, sqlite3
from pathlib import Path
from typing import Any, Iterable, Iterator
from contextlib import contextmanager
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_MAX_RECORD_BYTES = 2 * 1024 * 1024
_AAD = b"MKAOS-CRYPTO-RAG-v1"

class CryptoRAGError(ValueError):
    """Invalid key, record, or encrypted-store operation."""

def key_from_env(name: str = "MKAOS_CRYPTO_RAG_KEY") -> bytes:
    raw = os.environ.get(name, "")
    if not raw:
        raise CryptoRAGError(f"{name} is required; encrypted RAG stays disabled.")
    try:
        key = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise CryptoRAGError(f"{name} must be valid Base64.") from exc
    if len(key) != 32:
        raise CryptoRAGError(f"{name} must decode to exactly 32 bytes.")
    return key

def generate_key() -> str:
    """Return a one-time key value for an operator to store outside the database."""
    return base64.b64encode(secrets.token_bytes(32)).decode("ascii")

def _finite_vector(vector: Iterable[float]) -> list[float]:
    try:
        values = [float(v) for v in vector]
    except (TypeError, ValueError) as exc:
        raise CryptoRAGError("Embedding must be a numeric vector.") from exc
    if not values or len(values) > 65536 or not all(math.isfinite(v) for v in values):
        raise CryptoRAGError("Embedding is empty, too large, or non-finite.")
    return values

class EncryptedVectorStore:
    """AES-256-GCM encrypted SQLite store with bounded cosine-similarity search."""
    def __init__(self, path: str | Path, key: bytes):
        if not isinstance(key, bytes) or len(key) != 32:
            raise CryptoRAGError("A 32-byte AES-256 key is required.")
        self.path = Path(path)
        if self.path.is_symlink():
            raise CryptoRAGError("Encrypted store path must not be a symlink.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cipher = AESGCM(key)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS encrypted_vectors (record_id TEXT PRIMARY KEY, nonce BLOB NOT NULL, ciphertext BLOB NOT NULL)")
        try:
            self.path.chmod(0o600)
        except OSError as exc:
            raise CryptoRAGError("Could not restrict encrypted database file permissions.") from exc

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=5)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA secure_delete=ON")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def upsert(self, *, record_id: str, embedding: Iterable[float], document: str,
               metadata: dict[str, Any] | None = None) -> None:
        self.upsert_many([{
            "record_id": record_id,
            "embedding": embedding,
            "document": document,
            "metadata": metadata,
        }])

    def upsert_many(self, records: Iterable[dict[str, Any]]) -> None:
        """Validate/encrypt a bounded batch before committing it atomically."""
        batch = list(records)
        if len(batch) > 10000:
            raise CryptoRAGError("At most 10,000 records can be written in one batch.")
        prepared = []
        for record in batch:
            if not isinstance(record, dict):
                raise CryptoRAGError("Each encrypted record must be an object.")
            record_id = record.get("record_id")
            embedding = record.get("embedding")
            document = record.get("document")
            metadata = record.get("metadata")
            if not isinstance(record_id, str) or not record_id or len(record_id) > 256:
                raise CryptoRAGError("record_id must be a non-empty string of at most 256 chars.")
            if not isinstance(document, str) or len(document.encode("utf-8")) > _MAX_RECORD_BYTES:
                raise CryptoRAGError("Document must be UTF-8 text under 2 MiB.")
            if metadata is not None and not isinstance(metadata, dict):
                raise CryptoRAGError("Metadata must be an object.")
            payload = json.dumps({
                "embedding": _finite_vector(embedding),
                "document": document,
                "metadata": metadata or {},
            }, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
            if len(payload) > _MAX_RECORD_BYTES:
                raise CryptoRAGError("Encrypted record exceeds the 2 MiB limit.")
            nonce = secrets.token_bytes(12)
            ciphertext = self._cipher.encrypt(nonce, payload, _AAD + record_id.encode("utf-8"))
            prepared.append((record_id, nonce, ciphertext))
        if not prepared:
            return
        with self._connect() as db:
            db.executemany(
                "INSERT INTO encrypted_vectors(record_id, nonce, ciphertext) VALUES (?, ?, ?) "
                "ON CONFLICT(record_id) DO UPDATE SET nonce=excluded.nonce, ciphertext=excluded.ciphertext",
                prepared,
            )

    def get(self, record_id: str) -> dict[str, Any] | None:
        """Return one authenticated record for migration and integrity checks."""
        with self._connect() as db:
            row = db.execute(
                "SELECT nonce, ciphertext FROM encrypted_vectors WHERE record_id=?",
                (record_id,),
            ).fetchone()
        if row is None:
            return None
        nonce, ciphertext = row
        try:
            raw = self._cipher.decrypt(nonce, ciphertext, _AAD + record_id.encode("utf-8"))
            item = json.loads(raw.decode("utf-8"))
            vector = _finite_vector(item.get("embedding", []))
            document = item.get("document")
            metadata = item.get("metadata", {})
            if not isinstance(document, str) or not isinstance(metadata, dict):
                raise ValueError("Invalid encrypted record payload.")
        except Exception as exc:
            raise CryptoRAGError("Encrypted record failed authentication or validation.") from exc
        return {"id": record_id, "embedding": vector, "document": document, "metadata": metadata}

    def count(self) -> int:
        """Return the number of encrypted records without decrypting payloads."""
        with self._connect() as db:
            row = db.execute("SELECT COUNT(*) FROM encrypted_vectors").fetchone()
        return int(row[0])

    def delete(self, record_id: str) -> bool:
        with self._connect() as db:
            cur = db.execute("DELETE FROM encrypted_vectors WHERE record_id=?", (record_id,))
            return cur.rowcount > 0

    def list_records(self) -> list[dict[str, Any]]:
        """Return all authenticated records for bounded pruning and offline audits."""
        with self._connect() as db:
            rows = db.execute("SELECT record_id, nonce, ciphertext FROM encrypted_vectors").fetchall()
        records = []
        for record_id, nonce, ciphertext in rows:
            try:
                raw = self._cipher.decrypt(nonce, ciphertext, _AAD + record_id.encode("utf-8"))
                item = json.loads(raw.decode("utf-8"))
                vector = _finite_vector(item.get("embedding", []))
                document = item.get("document")
                metadata = item.get("metadata", {})
                if not isinstance(document, str) or not isinstance(metadata, dict):
                    raise ValueError("Invalid encrypted record payload.")
            except Exception as exc:
                raise CryptoRAGError("Encrypted record failed authentication or validation.") from exc
            records.append({"id": record_id, "embedding": vector, "document": document, "metadata": metadata})
        return records

    def search(self, query_embedding: Iterable[float], *, limit: int = 5,
               metadata_filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        query = _finite_vector(query_embedding)
        if metadata_filter is not None and not isinstance(metadata_filter, dict):
            raise CryptoRAGError("metadata_filter must be an object.")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise CryptoRAGError("limit must be an integer between 1 and 100.")
        with self._connect() as db:
            rows = db.execute("SELECT record_id, nonce, ciphertext FROM encrypted_vectors").fetchall()
        ranked = []
        qnorm = math.sqrt(sum(v * v for v in query))
        for record_id, nonce, ciphertext in rows:
            try:
                raw = self._cipher.decrypt(nonce, ciphertext, _AAD + record_id.encode("utf-8"))
                item = json.loads(raw.decode("utf-8"))
            except Exception as exc:
                raise CryptoRAGError("Encrypted record failed authentication; refusing to skip it.") from exc
            metadata = item.get("metadata", {})
            if metadata_filter and any(metadata.get(key) != value for key, value in metadata_filter.items()):
                continue
            vector = _finite_vector(item.get("embedding", []))
            if len(vector) != len(query):
                continue
            vnorm = math.sqrt(sum(v * v for v in vector))
            score = sum(a * b for a, b in zip(query, vector)) / (qnorm * vnorm) if qnorm and vnorm else 0.0
            ranked.append((score, record_id, item))
        ranked.sort(key=lambda row: row[0], reverse=True)
        return [{"id": rid, "score": score, "document": item["document"], "metadata": item.get("metadata", {})} for score, rid, item in ranked[:limit]]
