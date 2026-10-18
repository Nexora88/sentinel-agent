import json
import tempfile
import unittest
from pathlib import Path

from tools.extract_common_voice_text import extract
from tools.evaluate_mkaos_turkish_tasks import evaluate, norm


class CommonVoiceExtractionTests(unittest.TestCase):
    def test_preserves_source_labels_and_does_not_assume_license(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "validated_sentences.tsv"
            path.write_text(
                "sentence_id\tsentence\tsource\n"
                "1\tMerhaba dünya.\tcommunity\n"
                "2\tMerhaba dünya.\tcommunity\n"
                "3\tBaşka bir cümle.\tbook\n",
                encoding="utf-8",
            )
            records, report = extract(
                path, release="test release", source_uri="https://example.org/product"
            )
        self.assertEqual(report["duplicate_normalized_sentences_removed"], 1)
        self.assertTrue(all(row["license_id"] == "unreviewed" for row in records))
        self.assertEqual({row["source_label"] for row in records}, {"community", "book"})
        self.assertTrue(all(row["human_review"] == "pending" for row in records))
        self.assertFalse(report["training_allowed"])


class TurkishTaskEvaluationTests(unittest.TestCase):
    def row(self, case_id, source_id, group, task="grammar"):
        return {
            "case_id": case_id,
            "task": task,
            "prompt": "Bu cümleyi değerlendir.",
            "reference": "Doğru bir cümle.",
            "prediction": "Doğru bir cümle.",
            "source_id": source_id,
            "document_group": group,
            "human_review": "approved",
            "split": "test",
            "human_score": 4,
        }

    def test_scores_without_emitting_raw_text(self):
        result = evaluate(
            [self.row("a", "source-a", "doc-a"), self.row("b", "source-b", "doc-b")],
            checkpoint_sha256="a" * 64,
        )
        self.assertEqual(result["cases"], 2)
        self.assertEqual(result["normalized_exact_match_rate"], 1.0)
        self.assertEqual(result["human_score_mean_0_to_4"], 4.0)
        self.assertNotIn("prompt", result)
        self.assertFalse(result["used_for_training_or_checkpoint_selection"])

    def test_normalization_preserves_turkish_dotless_i(self):
        self.assertNotEqual(norm("I"), norm("ı"))
        self.assertEqual(norm("İ"), norm("i̇"))

    def test_rejects_source_leakage(self):
        with self.assertRaisesRegex(ValueError, "source appears in multiple splits"):
            evaluate(
                [self.row("a", "same-source", "doc-a"),
                 {**self.row("b", "same-source", "doc-b"), "split": "validation"}],
                checkpoint_sha256="b" * 64,
            )

    def test_coding_debugging_and_source_accuracy_need_external_checks(self):
        rows = [
            {**self.row("code", "s1", "g1", "coding"),
             "automated_checks": [{"name": "unit-tests", "passed": True},
                                  {"name": "lint", "passed": False}]},
            {**self.row("debug", "s2", "g2", "debugging"),
             "automated_checks": [{"name": "regression-tests", "passed": True}]},
            {**self.row("source", "s3", "g3", "source_accuracy"),
             "automated_checks": [{"name": "citation-match", "passed": True}]},
        ]
        report = evaluate(rows, checkpoint_sha256="c" * 64)
        self.assertEqual(report["automated_checks"], 4)
        self.assertEqual(report["automated_checks_passed"], 3)
        self.assertEqual(report["tasks"]["coding"]["automated_check_pass_rate"], 0.5)

    def test_rejects_unverified_code_or_citation_task(self):
        with self.assertRaisesRegex(ValueError, "requires at least one automated check"):
            evaluate([self.row("code", "s1", "g1", "coding")], checkpoint_sha256="d" * 64)


if __name__ == "__main__":
    unittest.main()
