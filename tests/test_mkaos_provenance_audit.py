import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "audit_mkaos_provenance.py"


class ProvenanceAuditTests(unittest.TestCase):
    def test_generates_explicitly_incomplete_report_and_hashes_model_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "requirements.txt").write_text("example-package==1.2.3\n", encoding="utf-8")
            (root / "LICENSE").write_text("License needs human review.\n", encoding="utf-8")
            (root / "weights.bin").write_bytes(b"not-a-real-model")
            (root / "server.py").write_text('MODEL = "SmolLM2"\n', encoding="utf-8")
            output = root / "audit.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root), "--output", str(output)],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "INCOMPLETE_REQUIRES_HUMAN_REVIEW")
            self.assertEqual(report["summary"]["dependency_manifest_count"], 1)
            self.assertEqual(report["summary"]["model_asset_count"], 1)
            self.assertEqual(len(report["model_assets"][0]["sha256"]), 64)
            self.assertTrue(any(x["kind"] == "third_party_model_reference"
                                for x in report["references_requiring_review"]))
            self.assertTrue(report["known_gaps"])

    def test_strict_mode_fails_when_provenance_gates_are_unresolved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "audit.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root),
                 "--output", str(output), "--strict"],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
