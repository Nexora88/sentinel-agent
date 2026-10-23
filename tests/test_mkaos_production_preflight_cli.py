"""CLI regression tests for the production readiness preflight."""
from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "mkaos_production_preflight.py"


class ProductionPreflightCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def test_missing_model_hash_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "model.bin"
            model.write_bytes(b"test checkpoint")
            result = self.run_cli("--model", str(model), "--json")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('"ready": false', result.stdout)
            self.assertIn("expected hash is required", result.stdout)

    def test_matching_model_hash_passes_model_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "model.bin"
            payload = b"approved test checkpoint fixture"
            model.write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            result = self.run_cli("--model", str(model), "--model-sha256", digest, "--json")
            self.assertIn('"check": "model_sha256",\n      "ok": true', result.stdout)

    def test_mismatched_model_hash_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "model.bin"
            model.write_bytes(b"fixture")
            result = self.run_cli("--model", str(model), "--model-sha256", "0" * 64, "--json")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('"check": "model_sha256",\n      "ok": false', result.stdout)

    def test_probe_rejects_non_https_url(self) -> None:
        result = self.run_cli("--probe-url", "http://localhost:8443/health", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("probe URL must be https://", result.stdout)


if __name__ == "__main__":
    unittest.main()
