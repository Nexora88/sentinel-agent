import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.billing import BillingError, StripeBilling


class BillingSecurityTests(unittest.TestCase):
    def test_local_free_is_default_without_credentials(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(StripeBilling.configured())
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(BillingError):
                    StripeBilling(Path(tmp) / "state.json").create_checkout(username="alice", email="a@example.com")

    def test_webhook_signature_and_timestamp(self):
        with patch.dict("os.environ", {"STRIPE_WEBHOOK_SECRET": "test_secret"}):
            raw = json.dumps({"id": "evt_1", "type": "ignored", "data": {"object": {}}}).encode()
            timestamp = 1000
            digest = hmac.new(b"test_secret", str(timestamp).encode() + b"." + raw, hashlib.sha256).hexdigest()
            billing = StripeBilling()
            self.assertEqual(billing.verify_signature(raw, f"t={timestamp},v1={digest}", now=1000)["id"], "evt_1")
            with self.assertRaises(BillingError):
                billing.verify_signature(raw, f"t={timestamp},v1={digest}", now=2000)

    def test_duplicate_subscription_events_are_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            billing = StripeBilling(Path(tmp) / "state.json")
            event = {"id": "evt_2", "type": "customer.subscription.created",
                     "data": {"object": {"status": "active", "metadata": {"username": "alice"}}}}
            self.assertTrue(billing.process_event(event)["processed"])
            self.assertTrue(billing.process_event(event)["duplicate"])
            self.assertEqual(billing.status("alice")["tier"], "team_self_hosted")

    def test_event_without_bound_account_never_grants_team(self):
        with tempfile.TemporaryDirectory() as tmp:
            billing = StripeBilling(Path(tmp) / "state.json")
            event = {"id": "evt_3", "type": "customer.subscription.created",
                     "data": {"object": {"status": "active", "metadata": {}}}}
            billing.process_event(event)
            self.assertEqual(billing.status("alice")["tier"], "local_free")


if __name__ == "__main__":
    unittest.main()
