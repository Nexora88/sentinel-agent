#!/usr/bin/env python3
"""Compare fixed-test reports by category and reject mismatched datasets."""
import unittest

from tools.compare_mkaos_evaluations import compare


def report(dataset_hash, cases, accuracy, latency, repetition=0.1, memory=500):
    return {
        "dataset_id": "fixed-tr-001",
        "dataset_sha256": dataset_hash,
        "overall_heuristic_accuracy": accuracy,
        "latency_ms": {"median": latency, "p95": latency * 2},
        "peak_memory_mb": {"max": memory},
        "repetition": {"mean_repeated_4gram_ratio": repetition},
        "cases": cases,
    }


class CompareMkaosEvaluationTests(unittest.TestCase):
    def test_reports_compare_per_category_and_find_regressions(self):
        base_cases = [
            {"case_id": "instruction-1", "category": "instruction_following", "passed_heuristic": True},
            {"case_id": "fact-1", "category": "factuality", "passed_heuristic": False},
        ]
        new_cases = [
            {"case_id": "instruction-1", "category": "instruction_following", "passed_heuristic": False},
            {"case_id": "fact-1", "category": "factuality", "passed_heuristic": True},
        ]
        result = compare(report("abc", base_cases, 0.5, 100), report("abc", new_cases, 0.5, 80, repetition=0.05))
        self.assertEqual(result["regressed_case_ids"], ["instruction-1"])
        self.assertEqual(result["improved_case_ids"], ["fact-1"])
        self.assertEqual(result["by_category"]["instruction_following"]["delta"], -1.0)
        self.assertEqual(result["overall"]["median_latency_ms"]["delta_candidate_minus_baseline"], -20)
        self.assertAlmostEqual(result["overall"]["repetition_delta_candidate_minus_baseline"], -0.05)

    def test_rejects_reports_from_different_dataset_hashes(self):
        cases = [{"case_id": "a", "category": "logic", "passed_heuristic": True}]
        with self.assertRaisesRegex(ValueError, "dataset_sha256"):
            compare(report("abc", cases, 1.0, 10), report("def", cases, 1.0, 10))

    def test_rejects_mismatched_case_ids(self):
        a = [{"case_id": "a", "category": "logic", "passed_heuristic": True}]
        b = [{"case_id": "b", "category": "logic", "passed_heuristic": True}]
        with self.assertRaisesRegex(ValueError, "case IDs"):
            compare(report("abc", a, 1.0, 10), report("abc", b, 1.0, 10))


if __name__ == "__main__":
    unittest.main()
