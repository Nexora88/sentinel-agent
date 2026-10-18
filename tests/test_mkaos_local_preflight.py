import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.mkaos_local_preflight import build_report


class MkaosLocalPreflightTests(unittest.TestCase):
    def test_report_is_read_only_and_does_not_claim_training_approval(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            with patch("tools.mkaos_local_preflight._version", return_value={"available": False, "path": None, "version": None}), patch(
                "tools.mkaos_local_preflight._available_ram_bytes", return_value=1024
            ):
                report = build_report(Path(directory))
        self.assertFalse(report["network_used"])
        self.assertFalse(report["inference_started"])
        self.assertFalse(report["training_started"])
        self.assertIn("UNCHANGED", report["training_gate"])
        self.assertFalse(report["checkpoint"]["configured"])

    def test_checkpoint_hash_is_verified_in_bounded_memory_helper(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "tiny-checkpoint.bin"
            checkpoint.write_bytes(b"mkaos-test-fixture")
            digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
            env = {
                "MKAOS_NATIVE_CHECKPOINT": str(checkpoint),
                "MKAOS_NATIVE_SHA256": digest,
            }
            with patch.dict(os.environ, env, clear=True), patch(
                "tools.mkaos_local_preflight._version",
                return_value={"available": False, "path": None, "version": None},
            ), patch("tools.mkaos_local_preflight._available_ram_bytes", return_value=None):
                report = build_report(Path(directory))
            self.assertTrue(report["checkpoint"]["exists"])
            self.assertTrue(report["checkpoint"]["sha256_verified"])

    def test_hash_mismatch_is_reported_not_approved(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "tiny-checkpoint.bin"
            checkpoint.write_bytes(b"mkaos-test-fixture")
            env = {
                "MKAOS_NATIVE_CHECKPOINT": str(checkpoint),
                "MKAOS_NATIVE_SHA256": "0" * 64,
            }
            with patch.dict(os.environ, env, clear=True), patch(
                "tools.mkaos_local_preflight._version",
                return_value={"available": False, "path": None, "version": None},
            ), patch("tools.mkaos_local_preflight._available_ram_bytes", return_value=None):
                report = build_report(Path(directory))
            self.assertFalse(report["checkpoint"]["sha256_verified"])
            self.assertIn("mismatch", report["checkpoint"]["message"].lower())


if __name__ == "__main__":
    unittest.main()
