import tempfile
import unittest
from pathlib import Path

from core.crypto_rag import EncryptedVectorStore
from tools.migrate_crypto_rag import create_verified_backup, migrate_collection


class FakeCollection:
    def __init__(self, records):
        self.records = records

    def count(self):
        return len(self.records)

    def get(self, *, limit, offset, include):
        rows = self.records[offset:offset + limit]
        return {
            "ids": [row["id"] for row in rows],
            "documents": [row["document"] for row in rows],
            "metadatas": [row["metadata"] for row in rows],
            "embeddings": [row["embedding"] for row in rows],
        }


class CryptoRAGMigrationTests(unittest.TestCase):
    def test_migration_verifies_records_and_keeps_source(self):
        records = [
            {"id": "opaque-a", "document": "Türkçe özel içerik", "metadata": {"source": "not-a-secret-path", "n": 1}, "embedding": [0.1, 0.2]},
            {"id": "opaque-b", "document": "another private document", "metadata": {"kind": "test"}, "embedding": [0.3, 0.4]},
        ]
        source = FakeCollection(records)
        with tempfile.TemporaryDirectory() as tmp:
            store = EncryptedVectorStore(Path(tmp) / "encrypted.sqlite3", b"k" * 32)
            report = migrate_collection(source, store, batch_size=1)
            self.assertEqual(report["source_records"], 2)
            self.assertEqual(report["destination_records"], 2)
            self.assertEqual(report["verified_records"], 2)
            self.assertFalse(report["source_deleted"])
            self.assertEqual(source.count(), 2)
            self.assertEqual(store.get("opaque-a")["document"], "Türkçe özel içerik")

    def test_backup_must_be_new_and_matches_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "chroma"
            root.mkdir()
            (root / "data.bin").write_bytes(b"immutable-source")
            backup = Path(tmp) / "backup"
            digest = create_verified_backup(root, backup)
            self.assertEqual((backup / "data.bin").read_bytes(), b"immutable-source")
            self.assertEqual(len(digest), 64)
            with self.assertRaises(FileExistsError):
                create_verified_backup(root, backup)

    def test_migration_refuses_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = EncryptedVectorStore(Path(tmp) / "encrypted.sqlite3", b"k" * 32)
            store.upsert(record_id="existing", embedding=[1.0], document="keep me")
            with self.assertRaises(ValueError):
                migrate_collection(FakeCollection([]), store)


if __name__ == "__main__":
    unittest.main()
