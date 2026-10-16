"""Tests for the MKAOS-Mini profile and deterministic quality scorer."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.train_mkaos_profile import load_profile
from tools.evaluate_mkaos_answers import evaluate, read_answers, repetition_ratio
from tools.train_mkaos_from_scratch import VOCAB_SIZE, encode_documents, estimate_host_corpus_memory_bytes, estimate_parameter_count


ROOT = Path(__file__).resolve().parents[1]


class MkaosMiniProfileTests(unittest.TestCase):
    def test_corpus_memory_estimate_is_conservative_and_validated(self):
        self.assertGreaterEqual(estimate_host_corpus_memory_bytes(100), 512 * 1024 * 1024)
        with self.assertRaisesRegex(ValueError, "positive"):
            estimate_host_corpus_memory_bytes(0)

    def test_byte_tokens_use_compact_uint16_storage_and_preserve_eos(self):
        tokens = encode_documents(["çığ", "MKAOS"])
        self.assertEqual(tokens.typecode, "H")
        self.assertEqual(list(tokens), list("çığ".encode("utf-8")) + [256] + list(b"MKAOS") + [256])

    def test_profile_parameter_count_is_real_and_in_requested_range(self):
        profile = load_profile(ROOT / "configs/mkaos/train-135m.json")
        model = profile["model"]
        actual = estimate_parameter_count(
            VOCAB_SIZE, model["hidden_size"], model["layers"],
            model["heads"], model["kv_heads"], model["intermediate_size"],
        )
        self.assertEqual(actual, 133_194_752)
        self.assertEqual(actual, profile["expected_parameter_count"])
        self.assertGreaterEqual(actual, 100_000_000)
        self.assertLessEqual(actual, 500_000_000)

    def test_profile_runner_rejects_stale_parameter_count(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps({
                "schema_version": 1,
                "model": {"hidden_size": 64, "layers": 2, "heads": 4, "kv_heads": 2, "intermediate_size": 128},
                "training": {},
                "expected_parameter_count": 123,
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "parameter count mismatch"):
                load_profile(path)

    def test_evaluator_reports_category_scores_and_missing_cases(self):
        dataset = {
            "dataset_id": "test-fixed",
            "cases": [
                {"id": "instruction-1", "category": "instruction_following", "expected_contains": ["MKAOS TEST"]},
                {"id": "uncertainty-1", "category": "factuality", "expected_contains": ["doğrulayamam"]},
            ],
        }
        answers = {
            "instruction-1": {"case_id": "instruction-1", "answer": "MKAOS TEST 2026", "latency_ms": 12.0, "peak_memory_mb": 500},
        }
        report = evaluate(dataset, answers)
        self.assertEqual(report["cases_total"], 2)
        self.assertEqual(report["answers_received"], 1)
        self.assertEqual(report["missing_answer_ids"], ["uncertainty-1"])
        self.assertEqual(report["by_category"]["instruction_following"]["accuracy"], 1.0)
        self.assertEqual(report["by_category"]["factuality"]["accuracy"], 0.0)
        self.assertEqual(report["latency_ms"]["median"], 12.0)
        self.assertEqual(report["peak_memory_mb"]["max"], 500.0)

    def test_repetition_metric_detects_repeated_fourgrams(self):
        self.assertGreater(repetition_ratio("bir iki üç dört bir iki üç dört bir iki üç dört"), 0.0)

    def test_answer_reader_rejects_duplicate_case_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "answers.jsonl"
            path.write_text(
                '{"case_id":"x","answer":"one"}\n{"case_id":"x","answer":"two"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate answer"):
                read_answers(path)


if __name__ == "__main__":
    unittest.main()
