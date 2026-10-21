import hashlib
import os
import secrets
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.account_tokens import consume_token, _connect
from core.auth import AuthManager
from core.post_quantum_crypto import PostQuantumUnavailable, generate_kem_keypair


class AccountTokenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"MKAOS_ACCOUNT_TOKEN_DB": str(self.root / "tokens.sqlite3")}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.auth = AuthManager(str(self.root / "users.json"))
        self.auth.create_user("tester", "initial-password-123", display_name="Tester")
        self.auth.set_email("tester", "tester@example.test")

    def _token(self, purpose="reset"):
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO account_tokens(token_hash, username, purpose, expires_at, created_at, used_at) VALUES (?, ?, ?, strftime('%s','now') + 600, strftime('%s','now'), NULL)",
                (digest, "tester", purpose),
            )
            conn.commit()
        finally:
            conn.close()
        return token

    def test_password_reset_consumes_token_and_revokes_sessions(self):
        session = self.auth.authenticate("tester", "initial-password-123")
        self.assertIsNotNone(session)
        token = self._token("reset")
        self.assertTrue(consume_token(self.auth, token, "reset", "a-new-long-password-456"))
        self.assertFalse(consume_token(self.auth, token, "reset", "another-long-password-789"))
        self.assertIsNone(self.auth.validate(session))
        self.assertIsNotNone(self.auth.authenticate("tester", "a-new-long-password-456"))

    def test_email_verification_token_is_single_use(self):
        token = self._token("verify")
        self.assertTrue(consume_token(self.auth, token, "verify"))
        self.assertTrue(self.auth._users["tester"]["email_verified"])
        self.assertFalse(consume_token(self.auth, token, "verify"))

    def test_password_policy_rejects_short_password(self):
        self.assertFalse(self.auth.set_password("tester", "short"))

    def test_post_quantum_is_disabled_by_default(self):
        with patch.dict(os.environ, {"MKAOS_PQ_PROFILE": "disabled"}):
            with self.assertRaises(PostQuantumUnavailable):
                generate_kem_keypair()


if __name__ == "__main__":
    unittest.main()
