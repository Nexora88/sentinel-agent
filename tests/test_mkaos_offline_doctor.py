"""Unit tests for the read-only offline readiness checker."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.mkaos_offline_doctor import inspect_file, run_checks


class OfflineDoctorTests(unittest.TestCase):
    def test_hash_is_reported_and_optional_pin_is_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.bin"
            path.write_bytes(b"local checkpoint")
            digest = hashlib.sha256(b"local checkpoint").hexdigest()
            self.assertTrue(inspect_file("checkpoint", path, digest)["ok"])
            self.assertFalse(inspect_file("checkpoint", path)["ok"])
            self.assertEqual(inspect_file("checkpoint", path)["status"], "present_hash_not_pinned")
            self.assertEqual(inspect_file("checkpoint", path, "0" * 64)["status"], "sha256_mismatch")

    def test_missing_checkpoint_is_not_claimed_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docker-compose.offline.yml").write_text("services: {}", encoding="utf-8")
            (root / "engine/mkaos-inference").mkdir(parents=True)
            (root / "engine/mkaos-inference/Cargo.toml").write_text("[package]", encoding="utf-8")
            report = run_checks(root)
            self.assertFalse(report["core_ready"])
            checkpoint = next(row for row in report["checks"] if row["name"] == "native checkpoint")
            self.assertEqual(checkpoint["status"], "missing")

    def test_doctor_is_explicitly_read_only_and_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_checks(Path(tmp))
            self.assertEqual(report["mode"], "read-only-no-network")
            self.assertTrue(any("No network requests" in note for note in report["notes"]))


if __name__ == "__main__":
    unittest.main()
