import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.personal_memory import PersonalMemory


class EncryptedProfileTests(unittest.TestCase):
    def make_memory(self, root, encrypted):
        item = object.__new__(PersonalMemory)
        item.persist_directory = root
        item.encrypt_profile = encrypted
        item.profile_path = root / ("profile.enc" if encrypted else "profile.json")
        item.legacy_profile_path = root / "profile.json"
        item._profile = {"name": "Example", "projects": ["sample"], "facts": []}
        return item

    def test_encrypted_round_trip(self):
        key = base64.urlsafe_b64encode(bytes(range(32))).decode("ascii")
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"MKAOS_MEMORY_KEY": key}):
            root = Path(directory)
            item = self.make_memory(root, True)
            item._save_profile()
            self.assertNotIn(b"sample", item.profile_path.read_bytes())
            loaded = self.make_memory(root, True)._load_profile()
            self.assertEqual(loaded["projects"], ["sample"])

    def test_missing_key_fails_closed(self):
        key = base64.urlsafe_b64encode(bytes(range(32))).decode("ascii")
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"MKAOS_MEMORY_KEY": key}):
            root = Path(directory)
            self.make_memory(root, True)._save_profile()
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(RuntimeError):
                    self.make_memory(root, True)._load_profile()

    def test_plaintext_legacy_profile_requires_explicit_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "profile.json").write_text('{"name":"legacy"}', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Plaintext"):
                self.make_memory(root, True)._load_profile()

    def test_plaintext_mode_remains_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = self.make_memory(root, False)
            item._save_profile()
            self.assertIn(b"sample", item.profile_path.read_bytes())
            self.assertEqual(self.make_memory(root, False)._load_profile()["name"], "Example")


if __name__ == "__main__":
    unittest.main()
