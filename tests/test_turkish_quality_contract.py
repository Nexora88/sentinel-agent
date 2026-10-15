"""Deterministic contracts for Turkish-first and historically responsible model behavior."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TurkishQualityContractTests(unittest.TestCase):
    def test_quality_suite_contains_turkish_tasks(self):
        suite = json.loads((ROOT / "tests" / "fixtures" / "turkish_quality_tasks.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(suite), 11)
        self.assertTrue(all(item.get("prompt_tr") and item.get("category") for item in suite))
        self.assertTrue(any(any(ch in item["prompt_tr"] for ch in "çğıöşüÇĞİÖŞÜ") for item in suite))

    def test_historical_cases_cover_propaganda_and_legitimate_inquiry(self):
        suite = json.loads((ROOT / "tests" / "fixtures" / "turkish_quality_tasks.json").read_text(encoding="utf-8"))
        cases = {item["id"]: item for item in suite}
        self.assertIn("tr-history-001", cases)
        self.assertIn("tr-history-002", cases)
        self.assertIn("tr-history-003", cases)
        self.assertIn("do_not_invent_claims_or_sources", cases["tr-history-001"]["expected_checks"])
        self.assertIn("allow_legitimate_historical_inquiry", cases["tr-history-003"]["expected_checks"])

    def test_provenance_template_requires_hash_license_and_origin(self):
        manifest = json.loads((ROOT / "docs" / "model-provenance.template.json").read_text(encoding="utf-8"))
        for field in ("model_name", "version", "license_url", "weights_sha256", "origin_evidence_url", "verification_status"):
            self.assertIn(field, manifest)
        self.assertEqual(manifest["verification_status"], "unverified")


if __name__ == "__main__":
    unittest.main()
