"""Regression tests for the fail-closed MKAOS source-approval gate."""
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
    def test_project_owner_authorization_alone_does_not_open_gate(self):
        # The owner's intent is recorded but no source-specific evidence exists.
        registry = {
            "model_training_allowed": False,
            "current_approved_sources": [],
            "project_owner_authorization": {
                "status": "granted_by_project_owner_in_chat",
                "training_gate_effect": "no_change_until_source_specific_evidence_is_recorded",
            },
            "sources": [],
        }
        messages = validate_source_registry(sample_manifest(), registry)
        self.assertTrue(any("does not authorize model training" in e for e in messages))
        self.assertTrue(any("no explicitly approved source IDs" in e for e in messages))

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
        self.assertIn("does not replace independent legal", messages[0])


    def test_owner_authorized_local_experiment_is_explicit_and_nonredistributable(self):
        from core.mkaos_corpus_gate import validate_experimental_local_manifest
        manifest = {
            "data_rights_mode": "owner_supplied_local_nonredistributable",
            "source_kind": "owner_created_or_rights_cleared_local",
            "records": [{"source_id": "my-local-notes"}],
        }
        registry = {
            "project_owner_authorization": {"status": "granted_by_project_owner_in_chat"}
        }
        messages = validate_experimental_local_manifest(manifest, registry)
        self.assertEqual(len(messages), 1)
        self.assertIn("does NOT clear third-party rights", messages[0])

    def test_experimental_mode_rejects_third_party_candidate_sources(self):
        from core.mkaos_corpus_gate import validate_experimental_local_manifest
        manifest = {
            "data_rights_mode": "owner_supplied_local_nonredistributable",
            "source_kind": "third_party_dataset",
            "records": [{"source_id": "common-voice"}],
        }
        registry = {
            "project_owner_authorization": {"status": "granted_by_project_owner_in_chat"}
        }
        messages = validate_experimental_local_manifest(manifest, registry)
        self.assertTrue(any("source_kind" in message for message in messages))

    def test_experimental_mode_requires_explicit_data_rights_mode(self):
        from core.mkaos_corpus_gate import validate_experimental_local_manifest
        manifest = {
            "source_kind": "owner_created_or_rights_cleared_local",
            "records": [{"source_id": "my-local-notes"}],
        }
        registry = {
            "project_owner_authorization": {"status": "granted_by_project_owner_in_chat"}
        }
        messages = validate_experimental_local_manifest(manifest, registry)
        self.assertTrue(any("data_rights_mode" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
