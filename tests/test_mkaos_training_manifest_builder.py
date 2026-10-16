from __future__ import annotations

import json
import unittest

from tools.build_mkaos_training_manifest import build


def row(sample_id: str, split: str) -> dict[str, str]:
    return {
        "sample_id": sample_id,
        "text": f"Türkçe deneme cümlesi {sample_id}.",
        "source_id": "example-source",
        "source_uri": "https://example.org/dataset",
        "document_group": f"doc-{sample_id}",
        "license_id": "CC0-1.0",
        "consent": "open_license",
        "language": "tr",
        "topic": "general",
        "split": split,
        "human_review": "approved",
        "pii_status": "cleared",
    }


class BuildManifestTests(unittest.TestCase):
    def test_builds_trainer_compatible_manifest_without_approving_source(self):
        rows = [row("a", "train"), row("b", "validation"), row("c", "test")]
        corpus, manifest, report = build(
            [json.dumps(item, ensure_ascii=False) for item in rows],
            dataset_id="test-corpus",
            revision="test-revision",
            curator="test-reviewer",
            license_reviewed=False,
        )
        self.assertEqual(len(corpus), 3)
        self.assertEqual(manifest["license_reviewed"], False)
        self.assertEqual({item["split"] for item in manifest["records"]}, {"train", "validation", "test"})
        self.assertEqual(report["document_group_disjoint"], True)
        self.assertEqual(report["training_started"], False)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in manifest["records"]))

    def test_rejects_document_group_leakage(self):
        a = row("a", "train")
        b = row("b", "test")
        b["document_group"] = a["document_group"]
        with self.assertRaisesRegex(ValueError, "document group crosses splits"):
            build(
                [json.dumps(a), json.dumps(b), json.dumps(row("c", "validation"))],
                dataset_id="test-corpus",
                revision="test-revision",
                curator="test-reviewer",
                license_reviewed=False,
            )

    def test_rejects_pending_human_review(self):
        a, b, c = row("a", "train"), row("b", "validation"), row("c", "test")
        c["human_review"] = "pending"
        with self.assertRaisesRegex(ValueError, "human_review must be approved"):
            build(
                [json.dumps(a), json.dumps(b), json.dumps(c)],
                dataset_id="test-corpus",
                revision="test-revision",
                curator="test-reviewer",
                license_reviewed=False,
            )


if __name__ == "__main__":
    unittest.main()
