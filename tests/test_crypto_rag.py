import sqlite3, tempfile, unittest, base64, os
from pathlib import Path
from unittest.mock import patch
from core.crypto_rag import CryptoRAGError, EncryptedVectorStore, generate_key, key_from_env

class CryptoRAGTests(unittest.TestCase):
    def test_document_and_embedding_are_encrypted_at_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vectors.sqlite3"
            EncryptedVectorStore(path, b"k" * 32).upsert(record_id="r1", embedding=[1.0, 0.0], document="private vulnerability report text", metadata={"source": "private.py"})
            raw_files = [p.read_bytes() for p in Path(tmp).iterdir() if p.is_file()]
            self.assertTrue(raw_files)
            for raw in raw_files:
                self.assertNotIn(b"private vulnerability report text", raw)
                self.assertNotIn(b"private.py", raw)
            reopened = EncryptedVectorStore(path, b"k" * 32)
            self.assertEqual(reopened.count(), 1)
            self.assertEqual(reopened.get("r1")["embedding"], [1.0, 0.0])
            result = reopened.search([1.0, 0.0])
            self.assertEqual(result[0]["document"], "private vulnerability report text")
            self.assertEqual(result[0]["metadata"]["source"], "private.py")
    def test_wrong_key_and_tampering_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vectors.sqlite3"
            EncryptedVectorStore(path, b"a" * 32).upsert(record_id="r1", embedding=[0.1, 0.2], document="secret")
            with self.assertRaises(CryptoRAGError):
                EncryptedVectorStore(path, b"b" * 32).search([0.1, 0.2])
            with sqlite3.connect(path) as db:
                db.execute("UPDATE encrypted_vectors SET ciphertext=? WHERE record_id='r1'", (b"bad",))
            with self.assertRaises(CryptoRAGError):
                EncryptedVectorStore(path, b"a" * 32).search([0.1, 0.2])
    def test_symlink_database_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.sqlite3"
            target.write_bytes(b"not a database")
            link = root / "linked.sqlite3"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Symlink creation is unavailable on this runner.")
            with self.assertRaises(CryptoRAGError):
                EncryptedVectorStore(link, b"k" * 32)

    def test_limits_and_key_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = EncryptedVectorStore(Path(tmp) / "vectors.sqlite3", b"k" * 32)
            with self.assertRaises(CryptoRAGError): store.search([1.0], limit=0)
            with self.assertRaises(CryptoRAGError): store.upsert(record_id="x", embedding=[float("nan")], document="x")
        self.assertEqual(len(base64.b64decode(generate_key())), 32)
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(CryptoRAGError):
            key_from_env("MKAOS_TEST_MISSING_CRYPTO_RAG_KEY")

if __name__ == "__main__": unittest.main()
