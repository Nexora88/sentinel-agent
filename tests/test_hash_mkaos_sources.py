import csv
import tempfile
import unittest
from pathlib import Path

from tools.hash_mkaos_sources import inventory, render_tsv, verify_tsv


class SourceInventoryTests(unittest.TestCase):
    def test_inventory_is_sorted_and_hashes_actual_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "b.bin").write_bytes(b"second")
            (root / "a.bin").write_bytes(b"first")
            rows = inventory(root)
            self.assertEqual([row[0] for row in rows], ["a.bin", "b.bin"])
            self.assertEqual(rows[0][1], 5)
            self.assertEqual(len(rows[0][2]), 64)

    def test_tsv_verifies_then_detects_changed_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "archive.zip"
            source.write_bytes(b"original")
            manifest = root / "hashes.tsv"
            manifest.write_text(render_tsv(inventory(root, exclude=manifest)), encoding="utf-8")
            ok, issues = verify_tsv(root, manifest)
            self.assertTrue(ok, issues)
            source.write_bytes(b"changed")
            ok, issues = verify_tsv(root, manifest)
            self.assertFalse(ok)
            self.assertTrue(any("size/hash mismatch" in item for item in issues))

    def test_verifier_detects_missing_and_extra_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "one.tsv").write_text("one", encoding="utf-8")
            manifest = root / "hashes.tsv"
            manifest.write_text(render_tsv(inventory(root, exclude=manifest)), encoding="utf-8")
            (root / "two.tsv").write_text("two", encoding="utf-8")
            ok, issues = verify_tsv(root, manifest)
            self.assertFalse(ok)
            self.assertTrue(any("not recorded in TSV" in item for item in issues))


if __name__ == "__main__":
    unittest.main()
