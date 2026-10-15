import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.webauthn_auth import WebAuthnError, WebAuthnManager


class WebAuthnChallengeTests(unittest.TestCase):
    def make_manager(self, directory):
        return WebAuthnManager(str(Path(directory) / "credentials.json"))

    def test_challenge_is_bound_to_purpose_and_consumed_once(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = self.make_manager(directory)
            issued = manager._issue("register", "owner", b"test-challenge")
            consumed = manager._consume(issued["challenge_id"], "register")
            self.assertEqual(consumed["username"], "owner")
            with self.assertRaises(WebAuthnError):
                manager._consume(issued["challenge_id"], "register")

    def test_challenge_cannot_be_consumed_for_another_purpose(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = self.make_manager(directory)
            issued = manager._issue("register", "owner", b"test-challenge")
            with self.assertRaises(WebAuthnError):
                manager._consume(issued["challenge_id"], "authenticate")
            # Wrong-purpose attempts do not consume the valid challenge.
            self.assertEqual(manager._consume(issued["challenge_id"], "register")["purpose"], "register")

    def test_registration_challenge_is_bound_to_account(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = self.make_manager(directory)
            issued = manager._issue("register", "owner", b"test-challenge")
            with self.assertRaises(WebAuthnError):
                manager.verify_registration_for_user(issued["challenge_id"], {}, "other-user")

    def test_corrupt_credential_store_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "credentials.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                WebAuthnManager(str(path))

    def test_non_local_http_origin_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            "os.environ", {"WEBAUTHN_ORIGIN": "http://example.com", "WEBAUTHN_RP_ID": "example.com"}
        ):
            with self.assertRaises(ValueError):
                WebAuthnManager(str(Path(directory) / "credentials.json"))


if __name__ == "__main__":
    unittest.main()
