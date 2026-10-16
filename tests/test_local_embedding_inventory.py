import tempfile
import unittest
from pathlib import Path

from tools.hash_local_embedding_model import inventory_model, verify_inventory


class LocalEmbeddingInventoryTests(unittest.TestCase):
    def test_inventory_records_stable_sha256_and_sizes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "model"
            root.mkdir()
            (root / "config.json").write_text('{"model":"local"}', encoding="utf-8")
            (root / "weights.bin").write_bytes(b"local-weights-not-real")
            manifest = inventory_model(root)
            self.assertEqual(manifest["file_count"], 2)
            self.assertEqual(manifest["files"]["config.json"]["size_bytes"], len('{"model":"local"}'))
            self.assertEqual(verify_inventory(root, manifest), [])
            self.assertIn("pending_human", manifest["review_status"])

    def test_inventory_detects_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "model"
            root.mkdir()
            weight = root / "weights.bin"
            weight.write_bytes(b"original")
            manifest = inventory_model(root)
            weight.write_bytes(b"changed")
            errors = verify_inventory(root, manifest)
            self.assertTrue(any("SHA-256 mismatch" in error for error in errors))

    def test_inventory_detects_added_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "model"
            root.mkdir()
            (root / "config.json").write_text("{}", encoding="utf-8")
            manifest = inventory_model(root)
            (root / "unexpected.bin").write_bytes(b"x")
            errors = verify_inventory(root, manifest)
            self.assertTrue(any("File set mismatch" in error for error in errors))

    def test_empty_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "model"
            root.mkdir()
            with self.assertRaisesRegex(ValueError, "no regular files"):
                inventory_model(root)


if __name__ == "__main__":
    unittest.main()
