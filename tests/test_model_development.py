import unittest

from core.model_development import (
    ModelDevelopmentError, PromotionPolicy, curate_dataset, evaluate_promotion, normalize_record,
)


def record(source_id="source-a", prompt="Explain a safe test", response="Use a unit test."):
    return {
        "prompt": prompt, "response": response, "source_id": source_id,
        "source_uri": "https://example.org/dataset", "license_id": "CC-BY-4.0",
        "consent": True, "review_status": "approved",
    }


class ModelDevelopmentTests(unittest.TestCase):
    def test_accepts_auditable_permitted_record_and_hashes_content(self):
        item = normalize_record(record())
        self.assertEqual(len(item["content_sha256"]), 64)
        self.assertEqual(item["license_id"], "CC-BY-4.0")

    def test_rejects_unknown_license_missing_consent_and_sensitive_data(self):
        bad = record()
        bad["license_id"] = "UNKNOWN"
        with self.assertRaises(ModelDevelopmentError):
            normalize_record(bad)
        bad = record()
        bad["consent"] = False
        with self.assertRaises(ModelDevelopmentError):
            normalize_record(bad)
        bad = record()
        bad["sensitive_data"] = True
        with self.assertRaises(ModelDevelopmentError):
            normalize_record(bad)

    def test_curator_deduplicates_and_reports_invalid_records(self):
        result = curate_dataset([record(), record(), {"prompt": "missing fields"}])
        self.assertEqual(result["summary"]["accepted"], 1)
        self.assertEqual(result["summary"]["rejected"], 2)
        self.assertEqual(result["rejections"][0]["reason"], "duplicate_content")
        self.assertFalse(result["training_allowed"])

    def test_source_split_is_stable_and_never_splits_one_source_across_sets(self):
        items = [record(f"source-{i}", f"prompt {i}", f"response {i}") for i in range(40)]
        first, second = curate_dataset(items), curate_dataset(items)
        self.assertEqual([x["split"] for x in first["records"]], [x["split"] for x in second["records"]])
        per_source = {}
        for item in first["records"]:
            per_source.setdefault(item["source_id"], set()).add(item["split"])
        self.assertTrue(all(len(splits) == 1 for splits in per_source.values()))

    def test_candidate_is_blocked_without_human_approval_or_with_safety_failure(self):
        baseline = {"quality_score": 0.88, "latency_p95_ms": 100}
        candidate = {"quality_score": 0.90, "latency_p95_ms": 110}
        report = evaluate_promotion(baseline=baseline, candidate=candidate, test_examples=200,
                                    critical_safety_failures=0, human_review_approved=False)
        self.assertEqual(report["decision"], "blocked")
        self.assertFalse(report["deploy_automatically"])
        report = evaluate_promotion(baseline=baseline, candidate=candidate, test_examples=200,
                                    critical_safety_failures=1, human_review_approved=True)
        self.assertIn("critical_safety_failure", report["issues"])

    def test_promotion_requires_sufficient_held_out_evaluation(self):
        report = evaluate_promotion(
            baseline={"quality_score": 0.90, "latency_p95_ms": 100},
            candidate={"quality_score": 0.91, "latency_p95_ms": 100},
            test_examples=10, critical_safety_failures=0, human_review_approved=True,
            policy=PromotionPolicy(min_test_examples=100),
        )
        self.assertIn("held_out_test_set_too_small", report["issues"])


if __name__ == "__main__":
    unittest.main()
