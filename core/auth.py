"""
Simple multi-user authentication for Sentinel Web UI.
Roles: owner > admin > user > viewer
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class AuthManager:
    def __init__(self, users_file: str = "./memory/users.json"):
        self.users_file = Path(users_file)
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, dict] = {}  # token -> user info
        self._users = self._load()

        # Bootstrap owner from env if no users yet
        if not self._users:
            owner_pass = os.getenv("OWNER_PASSWORD", "sentinel-change-me")
            self.create_user("owner", owner_pass, role="owner", display_name="Owner")

    def _load(self) -> Dict:
        if self.users_file.exists():
            try:
                return json.loads(self.users_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save(self) -> None:
        self.users_file.write_text(
            json.dumps(self._users, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _hash(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()

    def create_user(
        self,
        username: str,
        password: str,
        role: str = "user",
        display_name: Optional[str] = None,
    ) -> bool:
        username = username.lower().strip()
        if username in self._users:
            return False
        salt = secrets.token_hex(16)
        self._users[username] = {
            "password_hash": self._hash(password, salt),
            "salt": salt,
            "role": role,
            "display_name": display_name or username,
            "created_at": datetime.utcnow().isoformat(),
            "active": True,
        }
        self._save()
        return True

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Returns session token or None."""
        username = username.lower().strip()
        user = self._users.get(username)
        if not user or not user.get("active"):
            return None
        if self._hash(password, user["salt"]) != user["password_hash"]:
            return None
        token = secrets.token_urlsafe(32)
        self.sessions[token] = {
            "username": username,
            "role": user["role"],
            "display_name": user["display_name"],
            "expires": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        }
        return token

    def validate(self, token: Optional[str]) -> Optional[dict]:
        if not token:
            return None
        session = self.sessions.get(token)
        if not session:
            return None
        if datetime.fromisoformat(session["expires"]) < datetime.utcnow():
            del self.sessions[token]
            return None
        return session

    def require_role(self, token: Optional[str], min_role: str = "user") -> Optional[dict]:
        order = {"viewer": 0, "user": 1, "admin": 2, "owner": 3}
        session = self.validate(token)
        if not session:
            return None
        if order.get(session["role"], -1) >= order.get(min_role, 99):
            return session
        return None

    def list_users(self) -> List[dict]:
        return [
            {
                "username": u,
                "role": d["role"],
                "display_name": d["display_name"],
                "active": d.get("active", True),
            }
            for u, d in self._users.items()
        ]

    def set_role(self, username: str, role: str) -> bool:
        if username not in self._users:
            return False
        self._users[username]["role"] = role
        self._save()
        return True
