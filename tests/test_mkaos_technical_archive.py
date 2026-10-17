from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mkaos" / "audit_technical_archive.py"


class TechnicalArchiveAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.archive = self.root / "python.zip"
        with zipfile.ZipFile(self.archive, "w") as zf:
            zf.writestr("sample.py", "print('safe test fixture')\n")
        self.file_list = self.root / "files.txt"
        self.file_list.write_text("sample.py\n", encoding="utf-8")
        self.sha_file = self.root / "sha.txt"
        self.sha_file.write_text(hashlib.sha256(self.archive.read_bytes()).hexdigest() + "  python.zip\n", encoding="utf-8")
        self.output = self.root / "report.json"

    def tearDown(self):
        self.temp.cleanup()

    def run_audit(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--archive", str(self.archive),
             "--file-list", str(self.file_list), "--sha-file", str(self.sha_file),
             "--language", "python", "--source-url", "https://example.invalid/python.zip",
             "--output", str(self.output)],
            capture_output=True, text=True, check=False,
        )

    def test_writes_report_and_keeps_training_blocked(self):
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(report["dataset"], "CodeSearchNet")
        self.assertEqual(report["archive"]["zip_entries_count"], 1)
        self.assertEqual(report["training_gate"], "BLOCKED")
        self.assertFalse(report["rights_review"]["training_permission_approved"])

    def test_rejects_checksum_mismatch(self):
        self.sha_file.write_text("0" * 64 + "  python.zip\n", encoding="utf-8")
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match", result.stderr)

    def test_rejects_unsafe_archive_path(self):
        self.file_list.write_text("../escape.py\n", encoding="utf-8")
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsafe archive path", result.stderr)

    def test_rejects_empty_file_list(self):
        self.file_list.write_text("\n", encoding="utf-8")
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Archive listing is empty", result.stderr)


if __name__ == "__main__":
    unittest.main()
