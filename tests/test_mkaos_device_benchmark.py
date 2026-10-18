import unittest
import json
import tempfile
from pathlib import Path

from tools.benchmark_mkaos_device import model_manifest_summary, percentile, summarize


class DeviceBenchmarkStatisticsTests(unittest.TestCase):
    def test_percentile_is_stable_for_sorted_and_unsorted_samples(self):
        self.assertEqual(percentile([9, 1, 5], 0.5), 5)
        self.assertEqual(percentile([1, 2, 3, 4, 5], 0.95), 4.8)

    def test_empty_percentile_returns_none(self):
        self.assertIsNone(percentile([], 0.5))

    def test_summary_ignores_missing_metrics(self):
        result = summarize(
            [{"latency_ms": 10}, {"latency_ms": 20}, {"latency_ms": None}],
            "latency_ms",
        )
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["median_ms"], 15)
        self.assertEqual(result["p95_ms"], 19.5)

    def test_model_manifest_summary_includes_parameter_and_runtime_provenance(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps({
                "model_id": "mkaos-test", "revision": "abc123", "parameter_count": 133194752,
                "precision": "bf16", "architecture": {"family": "gqa", "layers": 12,
                                                            "hidden_size": 1024, "vocab_size": 257},
                "private_path": "must-not-be-copied",
            }), encoding="utf-8")
            result = model_manifest_summary(path)
        self.assertEqual(result["parameter_count"], 133194752)
        self.assertEqual(result["architecture"]["layers"], 12)
        self.assertNotIn("private_path", result)


if __name__ == "__main__":
    unittest.main()
