"""Stripe Checkout and signed webhook handling for optional team subscriptions.

No card data is stored by MKAOS. The local/free tier works without Stripe credentials.
Configure STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_TEAM_PRICE_ID,
MKAOS_BILLING_SUCCESS_URL and MKAOS_BILLING_CANCEL_URL only on a trusted deployment.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


class BillingError(RuntimeError):
    pass


def _https_url(name: str) -> str:
    value = os.getenv(name, "").strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise BillingError(f"{name} must be a valid HTTPS URL.")
    return value


class StripeBilling:
    def __init__(self, state_path: str | Path | None = None) -> None:
        self.state_path = Path(state_path or os.getenv("MKAOS_BILLING_STATE", "./memory/billing-state.json"))
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def configured() -> bool:
        return all(os.getenv(k, "").strip() for k in (
            "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_TEAM_PRICE_ID",
            "MKAOS_BILLING_SUCCESS_URL", "MKAOS_BILLING_CANCEL_URL",
        ))

    def create_checkout(self, *, username: str, email: str) -> dict[str, str]:
        username = username.strip().lower()
        email = email.strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{1,63}", username):
            raise BillingError("Invalid account identifier.")
        if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise BillingError("A valid email address is required for team billing.")
        secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
        price = os.getenv("STRIPE_TEAM_PRICE_ID", "").strip()
        if not secret or not price:
            raise BillingError("Team billing is not configured; local/free mode remains available.")
        payload = {
            "mode": "subscription",
            "success_url": _https_url("MKAOS_BILLING_SUCCESS_URL"),
            "cancel_url": _https_url("MKAOS_BILLING_CANCEL_URL"),
            "customer_email": email,
            "client_reference_id": username,
            "line_items[0][price]": price,
            "line_items[0][quantity]": "1",
            "metadata[username]": username,
            "subscription_data[metadata][username]": username,
        }
        session = requests.Session()
        session.trust_env = False
        try:
            response = session.post(
                "https://api.stripe.com/v1/checkout/sessions",
                data=payload,
                auth=(secret, ""),
                timeout=(3, 10),
            )
            if response.status_code not in (200, 201):
                raise BillingError("Stripe Checkout could not be created.")
            data = response.json()
        except BillingError:
            raise
        except Exception as exc:
            raise BillingError("Billing provider is temporarily unavailable.") from exc
        finally:
            session.close()
        url = data.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "checkout.stripe.com":
            raise BillingError("Billing provider returned an invalid checkout URL.")
        return {"checkout_url": url, "session_id": str(data.get("id", ""))}

    def verify_signature(self, raw_body: bytes, signature_header: str, *, now: int | None = None) -> dict[str, Any]:
        secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
        if not secret:
            raise BillingError("Webhook verification is not configured.")
        parts: dict[str, list[str]] = {}
        for item in signature_header.split(","):
            key, sep, value = item.partition("=")
            if sep:
                parts.setdefault(key.strip(), []).append(value.strip())
        try:
            timestamp = int(parts["t"][0])
        except (KeyError, ValueError, IndexError) as exc:
            raise BillingError("Invalid webhook signature header.") from exc
        current = int(time.time()) if now is None else now
        if abs(current - timestamp) > 300:
            raise BillingError("Webhook signature timestamp is outside the allowed window.")
        signed = str(timestamp).encode() + b"." + raw_body
        expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(expected, item) for item in parts.get("v1", [])):
            raise BillingError("Webhook signature verification failed.")
        try:
            event = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BillingError("Webhook body is invalid JSON.") from exc
        if not isinstance(event, dict) or not isinstance(event.get("id"), str):
            raise BillingError("Webhook event schema is invalid.")
        return event

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"schema_version": 1, "processed_events": [], "accounts": {}}
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BillingError("Billing state is unreadable; preserve it for recovery.") from exc
        if not isinstance(state, dict) or not isinstance(state.get("accounts"), dict):
            raise BillingError("Billing state schema is invalid.")
        state.setdefault("processed_events", [])
        return state

    def _write_state(self, state: dict[str, Any]) -> None:
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.state_path.parent,
                                             prefix=".billing-", suffix=".tmp", delete=False) as temp:
                json.dump(state, temp, ensure_ascii=False, indent=2)
                temp.flush()
                os.fsync(temp.fileno())
                temp_name = temp.name
            try:
                os.chmod(temp_name, 0o600)
            except OSError:
                pass
            os.replace(temp_name, self.state_path)
            try:
                os.chmod(self.state_path, 0o600)
            except OSError:
                pass
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)

    def process_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event_id = event.get("id")
        event_type = event.get("type")
        if not isinstance(event_id, str) or not isinstance(event_type, str):
            raise BillingError("Invalid event.")
        obj = event.get("data", {}).get("object", {})
        if not isinstance(obj, dict):
            raise BillingError("Invalid event object.")
        if event_type not in {
            "checkout.session.completed", "customer.subscription.created",
            "customer.subscription.updated", "customer.subscription.deleted",
        }:
            return {"received": True, "processed": False}
        username = str(obj.get("metadata", {}).get("username") or obj.get("client_reference_id") or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{1,63}", username):
            # Do not grant entitlements without an account identity tied to the signed event.
            return {"received": True, "processed": False}
        state = self._read_state()
        if event_id in state["processed_events"]:
            return {"received": True, "processed": True, "duplicate": True}
        active = event_type != "customer.subscription.deleted" and obj.get("status", "active") in {"active", "trialing", "complete"}
        state["accounts"][username] = {
            "team_subscription": "active" if active else "inactive",
            "provider": "stripe",
            "updated_event": event_id,
        }
        state["processed_events"] = (state["processed_events"] + [event_id])[-5000:]
        self._write_state(state)
        return {"received": True, "processed": True}

    def status(self, username: str) -> dict[str, str]:
        state = self._read_state()
        account = state["accounts"].get(username.strip().lower(), {})
        return {"tier": "team_self_hosted" if account.get("team_subscription") == "active" else "local_free"}
