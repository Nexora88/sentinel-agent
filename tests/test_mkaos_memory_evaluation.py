import unittest

from tools.evaluate_mkaos_memory import score_ranking, summarize


class MkaosMemoryEvaluationTests(unittest.TestCase):
    def test_expected_fact_at_rank_one_is_full_hit(self):
        self.assertEqual(
            score_ranking(["edr_soil", "offline"], "edr_soil", 3),
            {"recall_at_k": 1.0, "reciprocal_rank": 1.0, "answer_context_hit": 1.0},
        )

    def test_expected_fact_outside_k_is_miss(self):
        self.assertEqual(
            score_ranking(["offline", "tenant", "kv_cache", "edr_soil"], "edr_soil", 3),
            {"recall_at_k": 0.0, "reciprocal_rank": 0.25, "answer_context_hit": 0.0},
        )

    def test_missing_expected_fact_is_zero(self):
        self.assertEqual(
            score_ranking(["offline"], "edr_soil", 3),
            {"recall_at_k": 0.0, "reciprocal_rank": 0.0, "answer_context_hit": 0.0},
        )

    def test_latency_summary_reports_median_and_p95(self):
        self.assertEqual(summarize([10, 20, 30])["median_ms"], 20)
        self.assertEqual(summarize([10, 20, 30])["p95_ms"], 29.0)
        self.assertIsNone(summarize([])["median_ms"])


if __name__ == "__main__":
    unittest.main()
