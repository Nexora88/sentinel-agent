import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "mkaos_production_preflight.py"


class ProductionPreflightTests(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--json", *map(str, args)],
            check=False, capture_output=True, text=True, timeout=10,
        )

    def test_baseline_is_preflight_only_and_never_claims_ready_deployment(self):
        result = self.run_script()
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0 if report["ready"] else 1)
        self.assertEqual(report["mode"], "preflight-only")
        self.assertIn("do not prove production security", report["notice"])

    def test_missing_network_configuration_fails_closed(self):
        result = self.run_script("--require-network-config")
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ready"])
        self.assertTrue(any(item["check"] == "env:MKAOS_PUBLIC_BASE_URL" and not item["ok"]
                            for item in report["checks"]))

    def test_model_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "checkpoint.bin"
            model.write_bytes(b"test-only-model")
            result = self.run_script("--model", model, "--model-sha256", "0" * 64)
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(next(item for item in report["checks"]
                                  if item["check"] == "model_sha256")["ok"])

    def test_matching_model_hash_passes_integrity_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "checkpoint.bin"
            model.write_bytes(b"test-only-model")
            digest = hashlib.sha256(model.read_bytes()).hexdigest()
            result = self.run_script("--model", model, "--model-sha256", digest)
            report = json.loads(result.stdout)
            self.assertTrue(next(item for item in report["checks"]
                                 if item["check"] == "model_sha256")["ok"])

    def test_same_migration_source_and_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "store.db"
            source.write_text("fixture", encoding="utf-8")
            result = self.run_script("--migration-source", source,
                                     "--migration-destination", source)
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(next(item for item in report["checks"]
                                  if item["check"] == "migration_paths")["ok"])


if __name__ == "__main__":
    unittest.main()
