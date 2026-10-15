"""Regression tests for the opt-in AES-GCM file primitive."""
import base64
import os
import tempfile
import unittest
from pathlib import Path

from core.encrypted_store import EncryptedFileStore, EncryptedStoreError


class EncryptedFileStoreTests(unittest.TestCase):
    def test_round_trip_and_no_plaintext_on_disk(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "memory.enc"
            key = os.urandom(32)
            secret = b"private user memory"
            store = EncryptedFileStore(path, key=key)
            store.write_bytes(secret)
            self.assertEqual(store.read_bytes(), secret)
            self.assertNotIn(secret, path.read_bytes())

    def test_wrong_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "memory.enc"
            EncryptedFileStore(path, key=os.urandom(32)).write_bytes(b"secret")
            with self.assertRaises(EncryptedStoreError):
                EncryptedFileStore(path, key=os.urandom(32)).read_bytes()

    def test_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "memory.enc"
            EncryptedFileStore(path, key=os.urandom(32)).write_bytes(b"secret")
            blob = bytearray(path.read_bytes())
            blob[-1] ^= 1
            path.write_bytes(blob)
            with self.assertRaises(EncryptedStoreError):
                EncryptedFileStore(path, key=os.urandom(32)).read_bytes()

    def test_missing_key_is_rejected(self):
        old = os.environ.pop("MKAOS_MEMORY_KEY", None)
        try:
            with self.assertRaises(EncryptedStoreError):
                EncryptedFileStore.from_environment("unused.enc")
        finally:
            if old is not None:
                os.environ["MKAOS_MEMORY_KEY"] = old

    def test_environment_key_requires_256_bits(self):
        old = os.environ.get("MKAOS_MEMORY_KEY")
        os.environ["MKAOS_MEMORY_KEY"] = base64.urlsafe_b64encode(b"x" * 32).decode("ascii")
        try:
            store = EncryptedFileStore.from_environment("unused.enc")
            self.assertEqual(len(store._key), 32)
        finally:
            if old is None:
                os.environ.pop("MKAOS_MEMORY_KEY", None)
            else:
                os.environ["MKAOS_MEMORY_KEY"] = old


if __name__ == "__main__":
    unittest.main()
