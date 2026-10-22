import hashlib
import hmac
import json
import os
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from core.billing import (
    BillingError,
    _verify_signature,
    apply_webhook,
    create_checkout_session,
    get_billing_status,
)


class BillingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "MKAOS_NETWORK_MODE": "networked",
            "ALLOW_BILLING": "true",
            "STRIPE_SECRET_KEY": "sk_test_unit_test_only",
            "STRIPE_PRICE_ID": "price_test_example",
            "STRIPE_WEBHOOK_SECRET": "whsec_unit_test_only",
            "MKAOS_PUBLIC_BASE_URL": "https://mkaos.example.test",
            "MKAOS_BILLING_STATE_PATH": os.path.join(self.tmp.name, "billing.sqlite3"),
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_checkout_requires_test_mode_and_returns_only_hosted_url(self):
        response = Mock()
        response.json.return_value = {"id": "cs_test_123", "url": "https://checkout.stripe.com/c/pay/cs_test_123", "livemode": False}
        response.raise_for_status.return_value = None
        with patch("core.billing.requests.post", return_value=response):
            result = create_checkout_session("tester")
        self.assertEqual(result["mode"], "test")
        self.assertEqual(result["url"], "https://checkout.stripe.com/c/pay/cs_test_123")

    def test_live_stripe_key_is_rejected(self):
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_live_not_allowed"}):
            with self.assertRaises(BillingError):
                create_checkout_session("tester")

    def test_webhook_signature_is_verified_and_event_is_idempotent(self):
        event = {
            "id": "evt_test_123",
            "livemode": False,
            "type": "checkout.session.completed",
            "data": {"object": {
                "client_reference_id": "tester",
                "mode": "subscription",
                "payment_status": "paid",
                "subscription": "sub_test_123",
                "customer": "cus_test_123",
            }},
        }
        payload = json.dumps(event, separators=(",", ":")).encode()
        timestamp = str(int(time.time()))
        signed = timestamp.encode() + b"." + payload
        signature = hmac.new(b"whsec_unit_test_only", signed, hashlib.sha256).hexdigest()
        header = f"t={timestamp},v1={signature}"
        with patch("core.billing._network_and_test_key", return_value="sk_test_unit_test_only"):
            first = apply_webhook(payload, header)
            second = apply_webhook(payload, header)
        self.assertEqual(first["status"], "processed")
        self.assertEqual(second["status"], "duplicate_ignored")
        self.assertEqual(get_billing_status("tester")["plan_status"], "active")

    def test_live_mode_webhook_is_rejected_even_with_a_valid_signature(self):
        event = {"id": "evt_live_123", "livemode": True, "type": "ignored", "data": {"object": {}}}
        payload = json.dumps(event, separators=(",", ":")).encode()
        timestamp = str(int(time.time()))
        signed = timestamp.encode() + b"." + payload
        signature = hmac.new(b"whsec_unit_test_only", signed, hashlib.sha256).hexdigest()
        with patch("core.billing._network_and_test_key", return_value="sk_test_unit_test_only"):
            with self.assertRaisesRegex(BillingError, "test-mode"):
                apply_webhook(payload, f"t={timestamp},v1={signature}")

    def test_bad_webhook_signature_is_rejected(self):
        with self.assertRaises(BillingError):
            _verify_signature(b'{"id":"evt_test"}', "t=1,v1=bad", "whsec_unit_test_only")


if __name__ == "__main__":
    unittest.main()
