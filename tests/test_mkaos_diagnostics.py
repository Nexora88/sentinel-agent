from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.diagnose_mkaos_training import (
    corpus_benchmark,
    estimate_training_bytes,
    model_parameters,
)


class MkaosDiagnosticsTests(unittest.TestCase):
    def test_parameter_estimate_is_positive_and_deterministic(self):
        first = model_parameters(257, 32, 1, 4, 2, 64)
        second = model_parameters(257, 32, 1, 4, 2, 64)
        self.assertEqual(first, second)
        self.assertGreater(first, 0)

    def test_invalid_head_dimensions_are_rejected(self):
        with self.assertRaises(ValueError):
            model_parameters(257, 30, 1, 4, 2, 64)

    def test_memory_estimate_increases_with_batch_and_sequence(self):
        params = model_parameters(257, 32, 1, 4, 2, 64)
        small = estimate_training_bytes(params, 1, 32, 32, 1, 64)
        larger = estimate_training_bytes(params, 2, 64, 32, 1, 64)
        self.assertGreater(larger, small)

    def test_corpus_throughput_counts_utf8_bytes_and_eos(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus.jsonl"
            corpus.write_text(
                json.dumps({"sample_id": "a", "text": "Türkçe"}, ensure_ascii=False) + "\n"
                + json.dumps({"sample_id": "b", "text": "MKAOS"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            result = corpus_benchmark(corpus, 0)
        self.assertEqual(result["records_seen_including_malformed"], 2)
        self.assertEqual(result["valid_text_utf8_bytes"], len("Türkçe".encode("utf-8")) + len("MKAOS".encode("utf-8")))
        self.assertEqual(result["byte_tokens_including_eos"], result["valid_text_utf8_bytes"] + 2)
        self.assertEqual(result["malformed_records"], 0)
        self.assertGreater(result["byte_tokens_per_second"], 0)

    def test_sample_limit_does_not_read_all_records(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus.jsonl"
            corpus.write_text(
                json.dumps({"sample_id": "a", "text": "first"}) + "\n"
                + json.dumps({"sample_id": "b", "text": "second"}) + "\n",
                encoding="utf-8",
            )
            result = corpus_benchmark(corpus, 1)
        self.assertEqual(result["records_seen_including_malformed"], 1)
        self.assertEqual(result["valid_text_utf8_bytes"], len("first"))
        self.assertIsNotNone(result["sample_limit"])


if __name__ == "__main__":
    unittest.main()
