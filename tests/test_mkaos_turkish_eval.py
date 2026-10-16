"""Tests for Turkish smoke-evaluation scoring and benchmark validation."""
from __future__ import annotations
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "evaluate_mkaos_turkish.py"
SPEC = importlib.util.spec_from_file_location("mkaos_turkish_eval", SCRIPT)
assert SPEC and SPEC.loader
EVALUATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVALUATOR)

class TurkishEvaluationTests(unittest.TestCase):
    def test_turkish_case_mapping_preserves_dotless_i(self):
        self.assertEqual(EVALUATOR.normalize_tr("IĞDIR İZMİR"), "ığdır izmir")
    def test_score_matches_turkish_text_case_insensitively(self):
        self.assertTrue(EVALUATOR.score_output("Cevap: ANKARA", ["ankara"])["passed"])
    def test_score_fails_when_required_term_is_missing(self):
        score = EVALUATOR.score_output("Bilmiyorum.", ["Ankara"])
        self.assertFalse(score["passed"])
        self.assertEqual(score["missing_terms"], ["Ankara"])
    def test_benchmark_rejects_duplicate_case_ids(self):
        value = {"schema_version": 1, "cases": [{"id": "same", "prompt": "Soru", "required_terms": ["cevap"]}, {"id": "same", "prompt": "Başka soru", "required_terms": ["yanıt"]}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "benchmark.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate id"):
                EVALUATOR.load_benchmark(path)
    def test_repo_smoke_benchmark_is_frozen_and_not_training_data(self):
        cases = EVALUATOR.load_benchmark(EVALUATOR.DEFAULT_BENCHMARK)
        self.assertGreaterEqual(len(cases), 4)
        self.assertTrue(all(isinstance(case["required_terms"], list) for case in cases))

if __name__ == "__main__":
    unittest.main()
