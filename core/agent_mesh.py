"""Transport-agnostic signed envelopes for a future private agent mesh.

Ed25519 provides message authenticity/integrity, not confidentiality. The transport must
still use mutually authenticated TLS and an explicit peer allowlist. This module does not
open sockets, execute remote code, or authorize tools.
"""
from __future__ import annotations

import base64
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


MAX_ENVELOPE_BYTES = 64 * 1024
MAX_TTL_SECONDS = 300
MAX_CLOCK_SKEW_SECONDS = 60
MAX_REPLAY_ENTRIES = 10_000


class MeshMessageError(ValueError):
    pass


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _contains_executable_fields(value: Any) -> bool:
    forbidden = {"shell", "command", "exec", "executable", "script", "raw_code"}
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or key.lower() in forbidden or _contains_executable_fields(item):
                return True
    elif isinstance(value, list):
        return any(_contains_executable_fields(item) for item in value)
    return False


@dataclass(frozen=True)
class VerifiedTask:
    sender_id: str
    recipient_id: str
    task_id: str
    task_type: str
    payload: dict[str, Any]
    issued_at: int
    expires_at: int


def sign_task(*, sender_id: str, recipient_id: str, task_id: str, task_type: str,
              payload: dict[str, Any], private_key: Ed25519PrivateKey,
              now: int | None = None, ttl_seconds: int = 120) -> dict[str, Any]:
    """Sign a data-only task envelope; arbitrary shell/code payloads are rejected."""
    issued = int(time.time() if now is None else now)
    ttl = max(1, min(int(ttl_seconds), MAX_TTL_SECONDS))
    if not all(isinstance(v, str) and v.strip() and len(v) <= 128
               for v in (sender_id, recipient_id, task_id, task_type)):
        raise MeshMessageError("Invalid task identity fields.")
    if task_type not in {"status", "research_summary", "code_review", "test_request", "plan"}:
        raise MeshMessageError("Task type is not in the mesh allowlist.")
    if not isinstance(payload, dict) or len(_canonical(payload)) > 48 * 1024:
        raise MeshMessageError("Task payload must be a bounded JSON object.")
    if _contains_executable_fields(payload):
        raise MeshMessageError("Executable payload fields are not allowed.")
    body = {"version": 1, "sender_id": sender_id, "recipient_id": recipient_id,
            "task_id": task_id, "task_type": task_type, "payload": payload,
            "issued_at": issued, "expires_at": issued + ttl}
    signature = private_key.sign(_canonical(body))
    return {**body, "signature": base64.b64encode(signature).decode("ascii")}


class MeshVerifier:
    """Verify sender identity, target, freshness, signature and one-time task ID."""

    def __init__(self, *, local_agent_id: str, trusted_peers: dict[str, Ed25519PublicKey]):
        if not local_agent_id:
            raise ValueError("local_agent_id is required")
        self.local_agent_id = local_agent_id
        self.trusted_peers = dict(trusted_peers)
        self._seen: OrderedDict[str, int] = OrderedDict()

    def verify(self, envelope: dict[str, Any], *, now: int | None = None) -> VerifiedTask:
        if not isinstance(envelope, dict) or len(_canonical(envelope)) > MAX_ENVELOPE_BYTES:
            raise MeshMessageError("Envelope is invalid or too large.")
        try:
            signature = base64.b64decode(envelope["signature"], validate=True)
            body = {k: v for k, v in envelope.items() if k != "signature"}
            sender = body["sender_id"]
            recipient = body["recipient_id"]
            task_id = body["task_id"]
            issued = int(body["issued_at"])
            expires = int(body["expires_at"])
            task_type = body["task_type"]
            payload = body["payload"]
            version = body["version"]
        except (KeyError, TypeError, ValueError) as exc:
            raise MeshMessageError("Malformed signed envelope.") from exc
        current = int(time.time() if now is None else now)
        if version != 1 or recipient != self.local_agent_id or sender not in self.trusted_peers:
            raise MeshMessageError("Unknown sender, wrong recipient, or unsupported envelope version.")
        if task_type not in {"status", "research_summary", "code_review", "test_request", "plan"}:
            raise MeshMessageError("Task type is not allowed.")
        if expires <= current or expires - issued > MAX_TTL_SECONDS or issued > current + MAX_CLOCK_SKEW_SECONDS:
            raise MeshMessageError("Task is expired or timestamp is invalid.")
        if not isinstance(payload, dict) or len(_canonical(payload)) > 48 * 1024:
            raise MeshMessageError("Task payload must be a bounded JSON object.")
        if _contains_executable_fields(payload):
            raise MeshMessageError("Executable task payloads are not allowed.")
        replay_key = sender + ":" + str(task_id)
        if replay_key in self._seen:
            raise MeshMessageError("Duplicate task rejected.")
        try:
            self.trusted_peers[sender].verify(signature, _canonical(body))
        except Exception as exc:
            raise MeshMessageError("Signature verification failed.") from exc
        self._seen[replay_key] = expires
        for key, expiry in list(self._seen.items()):
            if expiry <= current:
                self._seen.pop(key, None)
        while len(self._seen) > MAX_REPLAY_ENTRIES:
            self._seen.popitem(last=False)
        return VerifiedTask(sender, recipient, str(task_id), str(task_type), payload, issued, expires)
