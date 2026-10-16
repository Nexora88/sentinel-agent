"""PostgreSQL persistence for tenant-isolated, application-encrypted MKAOS memory.

Requires psycopg (v3) and cryptography only when this optional adapter is used.
This module does not apply migrations automatically and never stores plaintext payloads.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

_TENANT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_ROLES = {"system", "user", "assistant", "tool"}


class PostgresMemoryStore:
    """Synchronous PostgreSQL store with RLS tenant context and AES-GCM payloads."""

    def __init__(self, dsn: str | None = None, encryption_key: str | None = None, connection: Any = None):
        raw_key = encryption_key if encryption_key is not None else os.getenv("MKAOS_MEMORY_ENCRYPTION_KEY", "")
        if not raw_key:
            raise RuntimeError("MKAOS_MEMORY_ENCRYPTION_KEY is required; refusing plaintext persistence.")
        try:
            key = base64.urlsafe_b64decode(raw_key + "=" * (-len(raw_key) % 4))
        except (ValueError, TypeError) as exc:
            raise ValueError("MKAOS_MEMORY_ENCRYPTION_KEY must be URL-safe base64 for 32 random bytes.") from exc
        if len(key) != 32:
            raise ValueError("MKAOS_MEMORY_ENCRYPTION_KEY must decode to exactly 32 bytes.")
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as exc:
            raise RuntimeError("Install cryptography to use encrypted PostgreSQL memory.") from exc
        self._master_key = key
        self._aesgcm_type = AESGCM
        if connection is None:
            try:
                import psycopg
            except ImportError as exc:
                raise RuntimeError("Install psycopg[binary] to use PostgreSQL memory.") from exc
            target_dsn = dsn or os.getenv("MKAOS_POSTGRES_DSN", "")
            if not target_dsn:
                raise RuntimeError("MKAOS_POSTGRES_DSN is required.")
            self.connection = psycopg.connect(target_dsn)
            self._owns_connection = True
        else:
            self.connection = connection
            self._owns_connection = False

    @staticmethod
    def _tenant(tenant_id: str) -> str:
        tenant = str(tenant_id or "")
        if not _TENANT_RE.fullmatch(tenant):
            raise ValueError("Invalid authenticated tenant identifier.")
        return tenant

    def _cipher(self, tenant_id: str):
        tenant_key = hmac.new(
            self._master_key,
            b"MKAOS-POSTGRES-MEMORY-KEY-v1\0" + tenant_id.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return self._aesgcm_type(tenant_key)

    @staticmethod
    def _aad(table: str, tenant_id: str, record_id: str) -> bytes:
        if table not in {"sessions", "messages", "memories"}:
            raise ValueError("Unsupported ciphertext domain.")
        return f"MKAOS-v1|{table}|{tenant_id}|{record_id}".encode("utf-8")

    def _encrypt(self, tenant_id: str, table: str, record_id: str, payload: bytes) -> bytes:
        import secrets
        nonce = secrets.token_bytes(12)
        return nonce + self._cipher(tenant_id).encrypt(nonce, payload, self._aad(table, tenant_id, record_id))

    def _decrypt(self, tenant_id: str, table: str, record_id: str, payload: bytes) -> bytes:
        if not isinstance(payload, (bytes, bytearray)) or len(payload) < 29:
            raise ValueError("Encrypted payload is malformed.")
        nonce, ciphertext = bytes(payload[:12]), bytes(payload[12:])
        # Authentication failure is raised; corrupted ciphertext is never returned as text.
        return self._cipher(tenant_id).decrypt(nonce, ciphertext, self._aad(table, tenant_id, record_id))

    @contextmanager
    def _tenant_transaction(self, tenant_id: str) -> Iterator[Any]:
        tenant = self._tenant(tenant_id)
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                # SET LOCAL scope is transaction-bound and parameterized; do not accept a
                # tenant ID directly from an unauthenticated HTTP request.
                cursor.execute("SELECT set_config('mkaos.tenant_id', %s, true)", (tenant,))
            yield self.connection

    def create_session(self, tenant_id: str, metadata: dict[str, Any] | None = None) -> str:
        tenant = self._tenant(tenant_id)
        session_id = str(uuid.uuid4())
        metadata_bytes = self._encrypt(
            tenant, "sessions", session_id,
            json.dumps(metadata or {}, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        )
        with self._tenant_transaction(tenant):
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO mkaos_sessions (id, tenant_id, metadata_ciphertext) VALUES (%s, %s, %s)",
                    (session_id, tenant, metadata_bytes),
                )
        return session_id

    def append_message(self, tenant_id: str, session_id: str, role: str, content: str) -> str:
        tenant = self._tenant(tenant_id)
        try:
            session_key = str(uuid.UUID(str(session_id)))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("Invalid session ID.") from exc
        if role not in _ROLES:
            raise ValueError("Unsupported message role.")
        if not isinstance(content, str):
            raise TypeError("Message content must be text.")
        message_id = str(uuid.uuid4())
        ciphertext = self._encrypt(tenant, "messages", message_id, content.encode("utf-8"))
        with self._tenant_transaction(tenant):
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO mkaos_messages (id, tenant_id, session_id, role, content_ciphertext) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (message_id, tenant, session_key, role, ciphertext),
                )
                cursor.execute(
                    "UPDATE mkaos_sessions SET updated_at = now() WHERE id = %s AND tenant_id = %s",
                    (session_key, tenant),
                )
                if cursor.rowcount != 1:
                    raise LookupError("Session does not exist in this tenant.")
        return message_id

    def list_messages(self, tenant_id: str, session_id: str, limit: int = 100) -> list[dict[str, Any]]:
        tenant = self._tenant(tenant_id)
        if not 1 <= int(limit) <= 1000:
            raise ValueError("limit must be between 1 and 1000.")
        session_key = str(uuid.UUID(str(session_id)))
        with self._tenant_transaction(tenant):
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, role, content_ciphertext, created_at FROM mkaos_messages "
                    "WHERE tenant_id = %s AND session_id = %s ORDER BY created_at, id LIMIT %s",
                    (tenant, session_key, int(limit)),
                )
                rows = cursor.fetchall()
        return [
            {
                "id": str(row[0]),
                "role": row[1],
                "content": self._decrypt(tenant, "messages", str(row[0]), row[2]).decode("utf-8"),
                "created_at": row[3].isoformat() if row[3] else None,
            }
            for row in rows
        ]

    def put_memory(
        self,
        tenant_id: str,
        payload: dict[str, Any],
        memory_id: str | None = None,
        memory_kind: str = "fact",
        source_session_id: str | None = None,
        embedding: bytes | None = None,
        embedding_model_id: str | None = None,
    ) -> str:
        tenant = self._tenant(tenant_id)
        key = str(uuid.UUID(str(memory_id))) if memory_id else str(uuid.uuid4())
        encrypted_payload = self._encrypt(
            tenant, "memories", key,
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        )
        encrypted_embedding = self._encrypt(tenant, "memories", key + ":embedding", embedding) if embedding else None
        source_session = str(uuid.UUID(str(source_session_id))) if source_session_id else None
        with self._tenant_transaction(tenant):
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO mkaos_memories "
                    "(id, tenant_id, memory_kind, payload_ciphertext, embedding_ciphertext, embedding_model_id, source_session_id) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (id) DO UPDATE SET payload_ciphertext = EXCLUDED.payload_ciphertext, "
                    "embedding_ciphertext = EXCLUDED.embedding_ciphertext, embedding_model_id = EXCLUDED.embedding_model_id, "
                    "memory_kind = EXCLUDED.memory_kind, updated_at = now() "
                    "WHERE mkaos_memories.tenant_id = EXCLUDED.tenant_id",
                    (key, tenant, memory_kind, encrypted_payload, encrypted_embedding, embedding_model_id, source_session),
                )
                if cursor.rowcount != 1:
                    raise PermissionError("Memory ID belongs to another tenant or could not be written.")
        return key

    def list_memories(self, tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
        tenant = self._tenant(tenant_id)
        if not 1 <= int(limit) <= 1000:
            raise ValueError("limit must be between 1 and 1000.")
        with self._tenant_transaction(tenant):
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, memory_kind, payload_ciphertext, embedding_model_id, source_session_id, created_at "
                    "FROM mkaos_memories WHERE tenant_id = %s ORDER BY updated_at DESC, id LIMIT %s",
                    (tenant, int(limit)),
                )
                rows = cursor.fetchall()
        return [
            {
                "id": str(row[0]),
                "kind": row[1],
                "payload": json.loads(self._decrypt(tenant, "memories", str(row[0]), row[2]).decode("utf-8")),
                "embedding_model_id": row[3],
                "source_session_id": str(row[4]) if row[4] else None,
                "created_at": row[5].isoformat() if row[5] else None,
            }
            for row in rows
        ]

    def close(self) -> None:
        if self._owns_connection:
            self.connection.close()
