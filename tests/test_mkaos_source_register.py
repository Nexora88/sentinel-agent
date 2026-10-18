import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TurkishCorpusSourceRegisterTests(unittest.TestCase):
    def test_registry_does_not_claim_unreviewed_sources_are_approved(self):
        path = ROOT / "data" / "mkaos" / "source-register.json"
        registry = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(registry["schema_version"], 1)
        self.assertEqual(registry["current_approved_sources"], [])
        self.assertFalse(registry["corpus_ready"])
        self.assertFalse(registry["model_training_allowed"])
        self.assertGreaterEqual(len(registry["sources"]), 3)
        self.assertEqual(len(registry["model_registry"]), 2)
        for model in registry["model_registry"]:
            with self.subTest(model=model["model_id"]):
                self.assertIsNone(model["revision"])
                self.assertFalse(model["permitted_download_now"])
                self.assertFalse(model["permitted_inference_now"])
                self.assertFalse(model["permitted_finetuning_now"])
                self.assertFalse(model["permitted_redistribution_now"])
                self.assertNotEqual(model["status"], "approved")

        for source in registry["sources"]:
            with self.subTest(source=source["source_id"]):
                self.assertTrue(source["canonical_url"].startswith("https://"))
                self.assertFalse(source["permitted_use_now"])
                self.assertNotEqual(source["status"], "approved")
                self.assertTrue(source["review_required"])

    def test_register_contains_expected_cautionary_sources(self):
        registry = json.loads(
            (ROOT / "data" / "mkaos" / "source-register.json").read_text(encoding="utf-8")
        )
        source_ids = {item["source_id"] for item in registry["sources"]}
        self.assertIn("mozilla-common-voice-text", source_ids)
        self.assertIn("wikimedia-turkish-wikipedia", source_ids)
        self.assertIn("tatoeba-turkish-text", source_ids)


if __name__ == "__main__":
    unittest.main()

