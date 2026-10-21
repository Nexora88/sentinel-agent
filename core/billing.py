"""Stripe-hosted checkout and signed webhook processing (test mode only).

Card data never enters MKAOS. Live-mode Stripe keys are intentionally rejected in this
initial implementation; production billing needs separate legal, operational, and security review.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests

class BillingError(RuntimeError):
    """Billing is disabled or the provider response/signature is invalid."""


def _network_and_test_key() -> str:
    if os.getenv("MKAOS_NETWORK_MODE", "offline").strip().lower() not in {"networked", "online"}:
        raise BillingError("Ödeme testi için ağ modu açıkça etkinleştirilmelidir.")
    if os.getenv("ALLOW_BILLING", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        raise BillingError("Ödeme entegrasyonu açıkça etkinleştirilmemiş.")
    secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret.startswith("sk_test_"):
        raise BillingError("Bu sürüm yalnızca Stripe test anahtarlarını kabul eder.")
    return secret


def _state_path() -> Path:
    path = Path(os.getenv("MKAOS_BILLING_STATE_PATH", "./memory/billing.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_state_path(), timeout=10, isolation_level=None)
    try:
        os.chmod(_state_path(), 0o600)
    except OSError:
        pass
    connection.execute(
        "CREATE TABLE IF NOT EXISTS processed_events (event_id TEXT PRIMARY KEY, processed_at INTEGER NOT NULL)"
    )
    connection.execute(
        """CREATE TABLE IF NOT EXISTS subscriptions (
            username TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            updated_at INTEGER NOT NULL
        )"""
    )
    return connection


def get_billing_status(username: str) -> dict:
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT status, stripe_customer_id, stripe_subscription_id, updated_at FROM subscriptions WHERE username = ?",
            (username,),
        ).fetchone()
        if not row:
            return {"plan_status": "inactive", "provider": "stripe", "mode": "test"}
        return {
            "plan_status": row[0],
            "provider": "stripe",
            "mode": "test",
            "customer_id": row[1],
            "subscription_id": row[2],
            "updated_at": row[3],
        }
    finally:
        connection.close()


def create_checkout_session(username: str) -> dict:
    secret = _network_and_test_key()
    price_id = os.getenv("STRIPE_PRICE_ID", "").strip()
    base_url = os.getenv("MKAOS_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if not price_id.startswith("price_"):
        raise BillingError("STRIPE_PRICE_ID ile Stripe test fiyatı yapılandırılmalıdır.")
    parsed = urlsplit(base_url)
    if not parsed.netloc or not (parsed.scheme == "https" or parsed.hostname in {"localhost", "127.0.0.1"}):
        raise BillingError("MKAOS_PUBLIC_BASE_URL HTTPS veya yerel test adresi olmalıdır.")
    try:
        response = requests.post(
            "https://api.stripe.com/v1/checkout/sessions",
            auth=(secret, ""),
            data={
                "mode": "subscription",
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": "1",
                "client_reference_id": username,
                "metadata[username]": username,
                "subscription_data[metadata][username]": username,
                "success_url": f"{base_url}/?billing=success",
                "cancel_url": f"{base_url}/?billing=cancel",
            },
            headers={"Idempotency-Key": "mkaos-checkout-" + hashlib.sha256(f"{username}:{time.time_ns()}".encode()).hexdigest()},
            timeout=(3, 10),
            allow_redirects=False,
        )
        response.raise_for_status()
        data = response.json()
        checkout_url = data.get("url", "")
        checkout_host = urlsplit(checkout_url).hostname
        if not data.get("id", "").startswith("cs_test_") or checkout_host != "checkout.stripe.com":
            raise ValueError("unexpected checkout response")
        return {"status": "checkout_created", "provider": "stripe", "mode": "test", "url": checkout_url}
    except Exception:
        raise BillingError("Stripe test checkout oluşturulamadı; anahtar, test fiyatı ve bağlantıyı denetle.") from None


def _verify_signature(payload: bytes, signature_header: str, secret: str) -> dict:
    parts: dict[str, list[str]] = {}
    for item in (signature_header or "").split(","):
        if "=" in item:
            key, value = item.split("=", 1)
            parts.setdefault(key.strip(), []).append(value.strip())
    timestamps = parts.get("t", [])
    signatures = parts.get("v1", [])
    if not timestamps or not signatures or not timestamps[0].isdigit():
        raise BillingError("Geçersiz webhook imzası.")
    timestamp = int(timestamps[0])
    if abs(int(time.time()) - timestamp) > 300:
        raise BillingError("Webhook imzası zaman aralığı dışında.")
    signed_payload = str(timestamp).encode() + b"." + payload
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, signature) for signature in signatures):
        raise BillingError("Geçersiz webhook imzası.")
    try:
        event = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise BillingError("Webhook JSON biçimi geçersiz.") from None
    if not isinstance(event, dict) or not str(event.get("id", "")).startswith("evt_"):
        raise BillingError("Webhook olay kimliği geçersiz.")
    return event


def apply_webhook(payload: bytes, signature_header: str | None) -> dict:
    _network_and_test_key()
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if not secret.startswith("whsec_"):
        raise BillingError("Stripe test webhook sırrı yapılandırılmalıdır.")
    event = _verify_signature(payload, signature_header or "", secret)
    event_id = event["id"]
    event_type = event.get("type", "")
    obj = event.get("data", {}).get("object", {})
    if not isinstance(obj, dict):
        raise BillingError("Webhook olay içeriği geçersiz.")
    connection = _connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            "INSERT OR IGNORE INTO processed_events(event_id, processed_at) VALUES (?, ?)",
            (event_id, int(time.time())),
        )
        if cursor.rowcount == 0:
            connection.execute("COMMIT")
            return {"status": "duplicate_ignored", "mode": "test"}
        username = str(obj.get("client_reference_id") or obj.get("metadata", {}).get("username") or "").strip()
        subscription_id = obj.get("subscription") or obj.get("id")
        customer_id = obj.get("customer")
        if event_type == "checkout.session.completed":
            if username and obj.get("mode") == "subscription" and obj.get("payment_status") in {"paid", "no_payment_required"}:
                connection.execute(
                    """INSERT INTO subscriptions(username, status, stripe_customer_id, stripe_subscription_id, updated_at)
                    VALUES (?, 'active', ?, ?, ?)
                    ON CONFLICT(username) DO UPDATE SET status='active',
                    stripe_customer_id=excluded.stripe_customer_id,
                    stripe_subscription_id=excluded.stripe_subscription_id,
                    updated_at=excluded.updated_at""",
                    (username, customer_id, subscription_id, int(time.time())),
                )
        elif event_type in {"customer.subscription.updated", "customer.subscription.deleted"}:
            status = str(obj.get("status", "inactive"))
            if event_type == "customer.subscription.deleted" or status not in {"active", "trialing"}:
                status = "inactive"
            if username:
                connection.execute(
                    """INSERT INTO subscriptions(username, status, stripe_customer_id, stripe_subscription_id, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(username) DO UPDATE SET status=excluded.status,
                    stripe_customer_id=COALESCE(excluded.stripe_customer_id, subscriptions.stripe_customer_id),
                    stripe_subscription_id=COALESCE(excluded.stripe_subscription_id, subscriptions.stripe_subscription_id),
                    updated_at=excluded.updated_at""",
                    (username, status, customer_id, subscription_id, int(time.time())),
                )
            elif subscription_id:
                connection.execute(
                    "UPDATE subscriptions SET status=?, updated_at=? WHERE stripe_subscription_id=?",
                    (status, int(time.time()), subscription_id),
                )
        connection.execute("COMMIT")
        return {"status": "processed", "event_type": event_type, "mode": "test"}
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()
