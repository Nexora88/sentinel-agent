"""Durable replay and peer-deny-list wrapper for the signed task verifier."""
from __future__ import annotations
import sqlite3
import time
from pathlib import Path
from typing import Any
from core.agent_mesh import MeshMessageError, MeshVerifier, VerifiedTask
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

class DurableMeshVerifier(MeshVerifier):
    """SQLite-backed atomic task-ID claims across process restarts on one host.

    For multi-host deployments, replace SQLite with a shared transactional store.
    """
    def __init__(self, *, local_agent_id: str, trusted_peers: dict[str, Ed25519PublicKey],
                 database_path: str, revoked_peer_ids: set[str] | None = None):
        if not database_path or database_path == ":memory:":
            raise ValueError("A persistent file-backed database_path is required")
        self.database_path = str(database_path)
        self.revoked_peer_ids = set(revoked_peer_ids or ())
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS seen_tasks (task_key TEXT PRIMARY KEY, expires_at INTEGER NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_seen_tasks_expiry ON seen_tasks(expires_at)")
        super().__init__(local_agent_id=local_agent_id, trusted_peers=trusted_peers)

    def revoke_peer(self, peer_id: str) -> None:
        if not isinstance(peer_id, str) or not peer_id.strip():
            raise ValueError("peer_id is required")
        self.revoked_peer_ids.add(peer_id)

    def verify(self, envelope: dict[str, Any], *, now: int | None = None) -> VerifiedTask:
        if not isinstance(envelope, dict):
            raise MeshMessageError("Envelope must be an object.")
        if envelope.get("sender_id") in self.revoked_peer_ids:
            raise MeshMessageError("Revoked peer rejected.")
        task = super().verify(envelope, now=now)
        current = int(time.time() if now is None else now)
        try:
            with sqlite3.connect(self.database_path, timeout=10, isolation_level="IMMEDIATE") as db:
                db.execute("PRAGMA busy_timeout=10000")
                db.execute("DELETE FROM seen_tasks WHERE expires_at <= ?", (current,))
                db.execute("INSERT INTO seen_tasks(task_key, expires_at) VALUES (?, ?)",
                           (task.sender_id + ":" + task.task_id, task.expires_at))
        except sqlite3.IntegrityError as exc:
            raise MeshMessageError("Duplicate task rejected by durable replay store.") from exc
        except sqlite3.Error as exc:
            raise MeshMessageError("Durable replay store unavailable; task rejected.") from exc
        return task
