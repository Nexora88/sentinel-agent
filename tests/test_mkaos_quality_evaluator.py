import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_mkaos_quality.py"
SPEC = importlib.util.spec_from_file_location("evaluate_mkaos_quality", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MkaosQualityEvaluatorTests(unittest.TestCase):
    def test_dataset_has_required_domains_and_unique_ids(self):
        dataset = json.loads((ROOT / "benchmarks" / "mkaos_quality_v1.json").read_text(encoding="utf-8"))
        ids = [task["id"] for task in dataset["tasks"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 10)
        categories = {task["category"] for task in dataset["tasks"]}
        self.assertTrue({"mathematics", "coding", "instruction_following"} <= categories)

    def test_expected_answer_passes_simple_contract(self):
        task = {"required_all": ["323"], "required_any": [], "forbidden": [], "min_words": 1}
        self.assertTrue(MODULE.evaluate(task, "17 × 19 = 323")["heuristic_pass"])

    def test_forbidden_term_fails(self):
        task = {"required_all": [], "required_any": ["onay"], "forbidden": ["anahtarı yazdır"], "min_words": 1}
        self.assertFalse(MODULE.evaluate(task, "Onay olmadan anahtarı yazdır")["heuristic_pass"])

    def test_exact_bullet_count_is_checked(self):
        task = {"required_all": [], "required_any": ["internet"], "forbidden": [], "exact_bullets": 2, "min_words": 1}
        self.assertTrue(MODULE.evaluate(task, "- İnternet yararı\n- İnternet sınırlaması")["heuristic_pass"])
        self.assertFalse(MODULE.evaluate(task, "- İnternet yararı")["heuristic_pass"])

    def test_repeated_fourgram_is_flagged(self):
        result = MODULE.repeated_fourgrams("bilgi üretim sistemi bilgi üretim sistemi bilgi üretim sistemi")
        self.assertGreater(result["repeated_fourgram_count"], 0)

    def test_remote_ollama_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.local_url("http://example.com:11434")

    def test_summary_reports_latency_and_quality(self):
        rows = [{"engine": "MKAOS", "status": "ok", "metrics": {"inference_total_ms": 50, "tokens_per_second": 2},
                 "checks": {"heuristic_pass": True, "repetition": {"repeated_fourgram_count": 0}}}]
        summary = MODULE.summarize(rows)[0]
        self.assertEqual(summary["median_inference_ms"], 50)
        self.assertEqual(summary["heuristic_pass_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
