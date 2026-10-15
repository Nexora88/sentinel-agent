import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.auth import AuthManager


class EncryptedAuthStoreTests(unittest.TestCase):
    def test_encrypted_account_store_round_trip(self):
        key = base64.urlsafe_b64encode(bytes(range(32))).decode("ascii")
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"MKAOS_MEMORY_KEY": key, "MKAOS_ENCRYPT_MEMORY_FILES": "true", "OWNER_PASSWORD": "test-long-password"},
        ):
            requested = Path(directory) / "users.json"
            manager = AuthManager(str(requested))
            encrypted_path = Path(directory) / "users.enc"
            self.assertTrue(encrypted_path.exists())
            self.assertNotIn(b"password_hash", encrypted_path.read_bytes())
            self.assertIsNotNone(manager.authenticate("owner", "test-long-password"))
            reloaded = AuthManager(str(requested))
            self.assertIsNotNone(reloaded.authenticate("owner", "test-long-password"))

    def test_plaintext_account_store_requires_explicit_migration(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"MKAOS_ENCRYPT_MEMORY_FILES": "true", "OWNER_PASSWORD": "test-long-password"}
        ):
            requested = Path(directory) / "users.json"
            requested.write_text('{"owner":{}}', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Plaintext"):
                AuthManager(str(requested))


if __name__ == "__main__":
    unittest.main()
