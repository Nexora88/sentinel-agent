import unittest
from tools.validate_mkaos_training_manifest import validate_manifest


def row(sample_id, digest, split):
    return {"sample_id": sample_id, "source_id": "source-1", "source_uri": "https://example.org/source", "license_id": "CC-BY-4.0", "consent": "open_license", "sha256": digest, "language": "tr", "topic": "general", "human_review": "approved", "pii_status": "cleared", "split": split}


def good_manifest():
    return {"schema_version": 1, "dataset_id": "mkaos-tr-demo", "revision": "0.1.0", "created_at": "2026-10-16", "curator": "review-team", "license_reviewed": True, "records": [row("train-1", "1" * 64, "train"), row("validation-1", "2" * 64, "validation"), row("test-1", "3" * 64, "test")]}


class TrainingManifestValidationTests(unittest.TestCase):
    def test_valid_manifest_is_metadata_only(self):
        messages = validate_manifest(good_manifest())
        self.assertEqual(len(messages), 1)
        self.assertIn("NOT legal clearance", messages[0])

    def test_pending_review_is_blocked(self):
        value = good_manifest()
        value["records"][0]["human_review"] = "pending"
        self.assertTrue(any("human_review" in message for message in validate_manifest(value)))

    def test_uncleared_pii_is_blocked(self):
        value = good_manifest()
        value["records"][0]["pii_status"] = "unknown"
        self.assertTrue(any("pii_status" in message for message in validate_manifest(value)))

    def test_duplicate_hash_is_blocked(self):
        value = good_manifest()
        value["records"][1]["sha256"] = value["records"][0]["sha256"]
        self.assertTrue(any("duplicates content" in message for message in validate_manifest(value)))

    def test_test_split_is_required(self):
        value = good_manifest()
        value["records"] = value["records"][:2]
        self.assertTrue(any("missing: test" in message for message in validate_manifest(value)))

    def test_https_source_is_required(self):
        value = good_manifest()
        value["records"][0]["source_uri"] = "http://example.org/source"
        self.assertTrue(any("HTTPS" in message for message in validate_manifest(value)))


    def test_unreviewed_owner_local_manifest_is_allowed_only_in_explicit_experimental_mode(self):
        value = good_manifest()
        value["license_reviewed"] = False
        value["data_rights_mode"] = "owner_supplied_local_nonredistributable"
        value["source_kind"] = "owner_created_or_rights_cleared_local"
        for record in value["records"]:
            record["source_uri"] = "local://owner-created-notes"
        self.assertTrue(any("license_reviewed" in message for message in validate_manifest(value)))
        messages = validate_manifest(value, experimental_local_only=True)
        self.assertEqual(len(messages), 1)
        self.assertIn("Experimental local-only mode", messages[0])
        self.assertIn("NOT legal clearance", messages[0])

    def test_experimental_mode_does_not_skip_pii_or_human_review(self):
        value = good_manifest()
        value["license_reviewed"] = False
        value["data_rights_mode"] = "owner_supplied_local_nonredistributable"
        value["source_kind"] = "owner_created_or_rights_cleared_local"
        value["records"][0]["pii_status"] = "unknown"
        messages = validate_manifest(value, experimental_local_only=True)
        self.assertTrue(any("pii_status" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
