import json
import unittest

from tools.prepare_mkaos_training_dataset import prepare_jsonl


def record(index: int, *, source_id: str | None = None) -> dict:
    return {
        "prompt": f"Türkçe soru {index}: kovan bakımı nasıl yapılır?",
        "response": f"Yanıt {index}: bakım kayıtlı ve denetlenebilir olmalıdır.",
        "source_id": source_id or f"source-{index}",
        "source_uri": f"dataset://licensed-tr/{source_id or f'source-{index}'}",
        "license_id": "CC-BY-4.0",
        "consent": True,
        "review_status": "approved",
    }


class TrainingDatasetCliTests(unittest.TestCase):
    def test_manifest_is_allowed_only_when_all_splits_have_examples(self):
        lines = [json.dumps(record(i), ensure_ascii=False) for i in range(100)]
        result = prepare_jsonl(lines)
        self.assertTrue(result["training_allowed"])
        counts = result["summary"]["split_counts"]
        self.assertGreater(counts["train"], 0)
        self.assertGreater(counts["validation"], 0)
        self.assertGreater(counts["test"], 0)
        self.assertEqual(result["summary"]["accepted"], 100)

    def test_records_from_same_source_never_cross_splits(self):
        rows = [record(i, source_id="same-source") for i in range(5)]
        result = prepare_jsonl([json.dumps(row) for row in rows])
        splits = {row["split"] for row in result["records"]}
        self.assertEqual(len(splits), 1)

    def test_invalid_json_and_unapproved_licence_are_rejected(self):
        bad_license = record(2)
        bad_license["license_id"] = "UNKNOWN"
        lines = [
            "{this is not json",
            json.dumps(record(1)),
            json.dumps(bad_license),
        ]
        result = prepare_jsonl(lines)
        self.assertEqual(result["summary"]["accepted"], 1)
        reasons = [item["reason"] for item in result["rejections"]]
        self.assertIn("invalid_json", reasons)
        self.assertTrue(any("license not allowlisted" in reason for reason in reasons))

    def test_duplicate_content_is_rejected_even_if_source_differs(self):
        first = record(1, source_id="source-a")
        duplicate = dict(first, source_id="source-b", source_uri="dataset://licensed-tr/source-b")
        result = prepare_jsonl([json.dumps(first), json.dumps(duplicate)])
        self.assertEqual(result["summary"]["accepted"], 1)
        self.assertIn("duplicate_content", [item["reason"] for item in result["rejections"]])

    def test_too_high_split_minimum_blocks_training(self):
        lines = [json.dumps(record(i), ensure_ascii=False) for i in range(30)]
        result = prepare_jsonl(lines, min_examples_per_split=100)
        self.assertFalse(result["training_allowed"])
        self.assertTrue(result["summary"]["split_gate_failures"])

    def test_consent_is_required(self):
        row = record(1)
        row["consent"] = False
        result = prepare_jsonl([json.dumps(row)])
        self.assertEqual(result["summary"]["accepted"], 0)
        self.assertFalse(result["training_allowed"])


if __name__ == "__main__":
    unittest.main()
