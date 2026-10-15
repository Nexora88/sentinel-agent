"""WebAuthn/passkey registration and authentication with one-time server challenges.

Credential private keys remain in the authenticator. This module stores only credential IDs,
public keys and counters. Production deployments must set a real HTTPS origin and RP ID.
"""
from __future__ import annotations

import base64
import json
import hashlib
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import options_to_json
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
)

class WebAuthnError(RuntimeError):
    pass


def _b64e(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64d(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class WebAuthnManager:
    def __init__(self, users_file: str = "./memory/webauthn_credentials.json"):
        self.users_file = Path(users_file)
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        self.rp_id = os.getenv("WEBAUTHN_RP_ID", "localhost").strip().lower()
        self.rp_name = os.getenv("WEBAUTHN_RP_NAME", "MKAOS Sentinel").strip() or "MKAOS Sentinel"
        self.origin = os.getenv("WEBAUTHN_ORIGIN", "http://localhost:8000").strip().rstrip("/")
        if not self.rp_id or "://" in self.rp_id or "/" in self.rp_id:
            raise ValueError("WEBAUTHN_RP_ID must be a hostname, not a URL.")
        if not self.origin.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise ValueError("WebAuthn origin must be HTTPS outside localhost.")
        if self.origin.startswith("http://") and not (
            self.origin.startswith("http://localhost") or self.origin.startswith("http://127.0.0.1")
        ):
            raise ValueError("HTTP WebAuthn is allowed only for localhost development.")
        self._lock = threading.RLock()
        self._challenges: dict[str, dict[str, Any]] = {}
        self._credentials = self._load()

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        if not self.users_file.exists():
            return {}
        try:
            data = json.loads(self.users_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or any(not isinstance(v, list) for v in data.values()):
                raise ValueError("invalid credential store schema")
            return data
        except Exception as exc:
            raise RuntimeError(f"WebAuthn credential store unreadable: {self.users_file}") from exc

    def _save(self) -> None:
        tmp = self.users_file.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(self._credentials, ensure_ascii=False, indent=2))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, self.users_file)
        try:
            os.chmod(self.users_file, 0o600)
        except OSError:
            pass

    def _issue(self, purpose: str, username: str, challenge: bytes) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            self._challenges = {k: v for k, v in self._challenges.items() if v["expires"] > now}
            challenge_id = secrets.token_urlsafe(24)
            self._challenges[challenge_id] = {
                "purpose": purpose, "username": username, "challenge": challenge, "expires": now + 180
            }
        return {"challenge_id": challenge_id}

    def _consume(self, challenge_id: str, purpose: str) -> dict[str, Any]:
        with self._lock:
            item = self._challenges.pop(challenge_id, None)
        if not item or item["expires"] <= time.time() or item["purpose"] != purpose:
            raise WebAuthnError("Challenge is missing, expired, or already used.")
        return item

    def registration_options(self, username: str, display_name: str) -> dict[str, Any]:
        username = username.lower().strip()
        if not username or len(username) > 128:
            raise WebAuthnError("Invalid username.")
        with self._lock:
            existing = self._credentials.get(username, [])
            options = generate_registration_options(
                rp_id=self.rp_id,
                rp_name=self.rp_name,
                user_id=hashlib.sha256(username.encode("utf-8")).digest(),
                user_name=username,
                user_display_name=(display_name or username)[:128],
                exclude_credentials=[
                    PublicKeyCredentialDescriptor(id=_b64d(item["credential_id"]))
                    for item in existing
                ],
                authenticator_selection=AuthenticatorSelectionCriteria(
                    resident_key=ResidentKeyRequirement.PREFERRED,
                    user_verification=UserVerificationRequirement.REQUIRED,
                ),
                timeout=60000,
            )
            challenge = options.challenge
            issued = self._issue("register", username, challenge)
        issued["publicKey"] = json.loads(options_to_json(options))
        return issued

    def verify_registration_for_user(self, challenge_id: str, credential: dict[str, Any], username: str) -> dict[str, Any]:
        """Bind passkey registration to the authenticated account that requested options."""
        with self._lock:
            item = self._challenges.get(challenge_id)
            if not item or item["username"] != username.lower().strip() or item["purpose"] != "register":
                raise WebAuthnError("Registration challenge does not belong to this account.")
        return self.verify_registration(challenge_id, credential)
    def verify_registration(self, challenge_id: str, credential: dict[str, Any]) -> dict[str, Any]:
        item = self._consume(challenge_id, "register")
        username = item["username"]
        try:
            verified = verify_registration_response(
                credential=credential,
                expected_challenge=item["challenge"],
                expected_rp_id=self.rp_id,
                expected_origin=self.origin,
                require_user_verification=True,
            )
        except Exception as exc:
            raise WebAuthnError("Passkey registration verification failed.") from exc
        credential_id = _b64e(verified.credential_id)
        with self._lock:
            records = self._credentials.setdefault(username, [])
            if any(x["credential_id"] == credential_id for x in records):
                raise WebAuthnError("This passkey is already registered.")
            records.append({
                "credential_id": credential_id,
                "public_key": _b64e(verified.credential_public_key),
                "sign_count": int(verified.sign_count),
                "created_at": int(time.time()),
            })
            self._save()
        return {"registered": True, "credential_count": len(records)}

    def authentication_options(self, username: str) -> dict[str, Any]:
        username = username.lower().strip()
        with self._lock:
            records = list(self._credentials.get(username, []))
        if not records:
            raise WebAuthnError("No passkey is registered for this account.")
        options = generate_authentication_options(
            rp_id=self.rp_id,
            allow_credentials=[
                PublicKeyCredentialDescriptor(id=_b64d(item["credential_id"]))
                for item in records
            ],
            user_verification=UserVerificationRequirement.REQUIRED,
            timeout=60000,
        )
        issued = self._issue("authenticate", username, options.challenge)
        issued["publicKey"] = json.loads(options_to_json(options))
        return issued

    def verify_authentication(self, challenge_id: str, credential: dict[str, Any]) -> str:
        item = self._consume(challenge_id, "authenticate")
        username = item["username"]
        credential_id = str(credential.get("id") or "")
        with self._lock:
            records = self._credentials.get(username, [])
            record = next((x for x in records if x["credential_id"] == credential_id), None)
            if not record:
                raise WebAuthnError("Passkey does not belong to this account.")
            try:
                verified = verify_authentication_response(
                    credential=credential,
                    expected_challenge=item["challenge"],
                    expected_rp_id=self.rp_id,
                    expected_origin=self.origin,
                    credential_public_key=_b64d(record["public_key"]),
                    credential_current_sign_count=int(record["sign_count"]),
                    require_user_verification=True,
                )
            except Exception as exc:
                raise WebAuthnError("Passkey authentication verification failed.") from exc
            new_count = int(verified.new_sign_count)
            # Some synced passkeys report a zero counter. Enforce monotonicity only when
            # the authenticator supplies a non-zero counter.
            if new_count and record["sign_count"] and new_count <= int(record["sign_count"]):
                raise WebAuthnError("Passkey signature counter did not advance.")
            record["sign_count"] = max(int(record["sign_count"]), new_count)
            self._save()
        return username

    def capabilities(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "rp_id": self.rp_id,
            "origin": self.origin,
            "registered_accounts": len(self._credentials),
            "challenge_ttl_seconds": 180,
            "private_keys_stored_server_side": False,
        }
