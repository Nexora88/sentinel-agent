import unittest

from core.mkaos_corpus_gate import validate_source_registry


def sample_manifest():
    return {"records": [{"source_id": "safe-source"}]}


def sample_registry():
    return {
        "model_training_allowed": True,
        "current_approved_sources": ["safe-source"],
        "sources": [{
            "source_id": "safe-source",
            "status": "approved",
            "permitted_use_now": True,
            "approved_revision": "release-1",
            "approval_evidence": "docs/approval-record.md",
            "weight_distribution_review": "approved",
        }],
    }


class MkaosCorpusGateTests(unittest.TestCase):
    def test_unapproved_source_blocks_training(self):
        registry = sample_registry()
        registry["current_approved_sources"] = []
        self.assertTrue(any("no explicitly approved source IDs" in e for e in validate_source_registry(sample_manifest(), registry)))

    def test_missing_weight_distribution_review_blocks_training(self):
        registry = sample_registry()
        registry["sources"][0]["weight_distribution_review"] = "pending"
        self.assertTrue(any("model-weight distribution" in e for e in validate_source_registry(sample_manifest(), registry)))

    def test_duplicate_source_ids_block_ambiguous_registry(self):
        registry = sample_registry()
        registry["sources"].append({**registry["sources"][0], "status": "blocked"})
        messages = validate_source_registry(sample_manifest(), registry)
        self.assertTrue(any("duplicate source_id" in message for message in messages))
        self.assertTrue(any("not explicitly approved" in message for message in messages))

    def test_malformed_manifest_source_id_blocks_training(self):
        messages = validate_source_registry({"records": [{"source_id": None}]}, sample_registry())
        self.assertTrue(any("needs a non-empty source_id" in message for message in messages))

    def test_approved_source_passes_with_warning(self):
        messages = validate_source_registry(sample_manifest(), sample_registry())
        self.assertEqual(len(messages), 1)
        self.assertTrue(messages[0].startswith("Source register checks passed"))


if __name__ == "__main__":
    unittest.main()
