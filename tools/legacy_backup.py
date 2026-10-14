"""
Legacy Mode — local encrypted backup of agent memory / profile.
Not blockchain. Not cloud. You control the passphrase and the file.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, 200_000, dklen=32)


def _xor_stream(data: bytes, key: bytes) -> bytes:
    # Simple stream (not AES). Good enough for local personal backup; use strong passphrase.
    out = bytearray()
    for i, b in enumerate(data):
        out.append(b ^ key[i % len(key)])
    return bytes(out)


class LegacyBackup:
    def __init__(self, memory_root: str = "./memory"):
        self.memory_root = Path(memory_root)

    def _collect_snapshot(self) -> Dict[str, Any]:
        snap: Dict[str, Any] = {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "version": 1,
            "files": {},
        }
        interesting = [
            "users.json",
            "curiosity_state.json",
            "universe/stats.json",
            "universe/seeds.json",
            "finance/paper_portfolio.json",
            "night_reports",
        ]
        for rel in interesting:
            p = self.memory_root / rel
            if p.is_file():
                try:
                    snap["files"][rel] = p.read_text(encoding="utf-8", errors="replace")[:500_000]
                except Exception:
                    pass
            elif p.is_dir():
                for f in sorted(p.glob("*.md"))[-5:]:
                    try:
                        snap["files"][f"{rel}/{f.name}"] = f.read_text(
                            encoding="utf-8", errors="replace"
                        )[:100_000]
                    except Exception:
                        pass
        return snap

    def export(self, passphrase: str, out_path: str = "./memory/legacy_backup.bin") -> str:
        if not passphrase or len(passphrase) < 8:
            raise ValueError("Passphrase must be at least 8 characters")
        snap = self._collect_snapshot()
        raw = json.dumps(snap, ensure_ascii=False).encode("utf-8")
        salt = secrets.token_bytes(16)
        key = _derive_key(passphrase, salt)
        cipher = _xor_stream(raw, key)
        blob = b"SNTL1" + salt + cipher
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(blob)
        return str(out.resolve())

    def import_preview(self, passphrase: str, path: str = "./memory/legacy_backup.bin") -> Dict:
        data = Path(path).read_bytes()
        if not data.startswith(b"SNTL1"):
            raise ValueError("Invalid backup format")
        salt = data[5:21]
        cipher = data[21:]
        key = _derive_key(passphrase, salt)
        raw = _xor_stream(cipher, key)
        return json.loads(raw.decode("utf-8"))
