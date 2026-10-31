from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mkaos_cli.scanner import scan_workspace


class ScannerTests(unittest.TestCase):
    def test_read_only_scan_redacts_secret_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sample.py"
            key_name = "API" + "_KEY"
            source.write_text(
                f'{key_name} = "ghp_12345678901234567890123456789012"\n',
                encoding="utf-8",
            )
            before = source.read_bytes()
            report = scan_workspace(root)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(report["files_scanned"], 1)
            self.assertEqual(report["findings"][0]["evidence"], "[REDACTED]")
            self.assertEqual(report["findings"][0]["rule"], "github-token")

    def test_env_files_are_not_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            password_name = "PASS" + "WORD"
            (root / ".env").write_text(
                f"{password_name}='super-secret-value'\n", encoding="utf-8"
            )
            report = scan_workspace(root)
            self.assertEqual(report["files_scanned"], 0)
            self.assertEqual(report["findings"], [])

    def test_rejects_file_target(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "file.txt"
            file_path.write_text("hello", encoding="utf-8")
            with self.assertRaises(ValueError):
                scan_workspace(file_path)


if __name__ == "__main__":
    unittest.main()
