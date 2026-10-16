"""Unit-level safety contracts for encrypted PostgreSQL memory (no database required)."""
import unittest

from core.postgres_memory_store import PostgresMemoryStore


class PostgresMemoryStoreCryptoTests(unittest.TestCase):
    def setUp(self):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        self.store = object.__new__(PostgresMemoryStore)
        self.store._master_key = bytes(range(32))
        self.store._aesgcm_type = AESGCM

    def test_ciphertext_round_trip_is_tenant_and_record_bound(self):
        clear = "Gizli kullanıcı belleği".encode("utf-8")
        encrypted = self.store._encrypt("u-alice", "messages", "message-1", clear)
        self.assertNotEqual(encrypted, clear)
        self.assertEqual(self.store._decrypt("u-alice", "messages", "message-1", encrypted), clear)
        with self.assertRaises(Exception):
            self.store._decrypt("u-bob", "messages", "message-1", encrypted)
        with self.assertRaises(Exception):
            self.store._decrypt("u-alice", "messages", "message-2", encrypted)

    def test_ciphertext_tampering_fails_closed(self):
        encrypted = bytearray(self.store._encrypt("u-alice", "memories", "memory-1", b"secret"))
        encrypted[-1] ^= 0x01
        with self.assertRaises(Exception):
            self.store._decrypt("u-alice", "memories", "memory-1", bytes(encrypted))

    def test_tenant_identifier_validation_rejects_path_and_control_input(self):
        for tenant in ("", "../owner", "alice/bob", "space user", "x" * 129):
            with self.subTest(tenant=tenant), self.assertRaises(ValueError):
                self.store._tenant(tenant)

    def test_tenant_key_derivation_is_stable_and_separate(self):
        self.assertNotEqual(
            self.store._cipher("u-alice").encrypt(b"\x00" * 12, b"payload", b"aad"),
            self.store._cipher("u-bob").encrypt(b"\x00" * 12, b"payload", b"aad"),
        )


if __name__ == "__main__":
    unittest.main()
