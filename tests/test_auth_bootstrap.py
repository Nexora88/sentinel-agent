import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.auth import AuthManager


class FirstRunPasswordTests(unittest.TestCase):
    def test_generated_password_is_recoverable_locally_and_authenticates(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"OWNER_PASSWORD": ""}):
            users_file = Path(directory) / "users.json"
            manager = AuthManager(users_file=str(users_file))
            password_file = Path(directory) / "first-run-password.txt"
            password = password_file.read_text(encoding="utf-8").strip()
            self.assertGreaterEqual(len(password), 24)
            self.assertIsNotNone(manager.authenticate("owner", password))
            self.assertEqual(password_file.stat().st_mode & 0o777, 0o600)

    def test_configured_password_does_not_create_bootstrap_secret(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"OWNER_PASSWORD": "test-only-long-password"}):
            users_file = Path(directory) / "users.json"
            manager = AuthManager(users_file=str(users_file))
            self.assertIsNotNone(manager.authenticate("owner", "test-only-long-password"))
            self.assertFalse((Path(directory) / "first-run-password.txt").exists())


if __name__ == "__main__":
    unittest.main()
