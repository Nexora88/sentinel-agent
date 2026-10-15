"""Small deterministic contract tests; not a substitute for model quality evaluation."""
import json
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

class TurkishQualityContractTests(unittest.TestCase):
    def test_quality_suite_contains_turkish_tasks(self):
        suite = json.loads((ROOT / "tests" / "fixtures" / "turkish_quality_tasks.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(suite), 8)
        self.assertTrue(all(item.get("prompt_tr") and item.get("category") for item in suite))
        self.assertTrue(any("İstanbul" in item["prompt_tr"] for item in suite))

    def test_provenance_template_requires_hash_license_and_origin(self):
        manifest = json.loads((ROOT / "docs" / "model-provenance.template.json").read_text(encoding="utf-8"))
        for field in ("model_name", "version", "license_url", "weights_sha256", "origin_evidence_url", "verification_status"):
            self.assertIn(field, manifest)
        self.assertEqual(manifest["verification_status"], "unverified")

if __name__ == "__main__": unittest.main()
