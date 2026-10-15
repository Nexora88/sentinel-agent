import unittest

from tools.benchmark_mkaos_device import percentile, summarize


class DeviceBenchmarkStatisticsTests(unittest.TestCase):
    def test_percentile_is_stable_for_sorted_and_unsorted_samples(self):
        self.assertEqual(percentile([9, 1, 5], 0.5), 5)
        self.assertEqual(percentile([1, 2, 3, 4, 5], 0.95), 5)

    def test_empty_percentile_returns_none(self):
        self.assertIsNone(percentile([], 0.5))

    def test_summary_ignores_missing_metrics(self):
        result = summarize(
            [{"latency_ms": 10}, {"latency_ms": 20}, {"latency_ms": None}],
            "latency_ms",
        )
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["median_ms"], 20)
        self.assertEqual(result["p95_ms"], 20)


if __name__ == "__main__":
    unittest.main()
