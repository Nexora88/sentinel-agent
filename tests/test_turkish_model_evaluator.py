import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_turkish_models.py"
SPEC = importlib.util.spec_from_file_location("evaluate_turkish_models", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EvaluatorTests(unittest.TestCase):
    def test_remote_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.local_base_url("http://example.com:11434")

    def test_local_endpoint_accepted(self):
        self.assertEqual(
            MODULE.local_base_url("http://localhost:11434/"),
            "http://localhost:11434",
        )

    def test_latency_percentiles_are_deterministic(self):
        values = [0.1, 0.2, 0.3, 0.4, 1.0]
        self.assertEqual(MODULE.percentile(values, 50), 0.3)
        self.assertEqual(MODULE.percentile(values, 95), 1.0)

    def test_empty_percentile_is_none(self):
        self.assertIsNone(MODULE.percentile([], 95))

    def test_heuristic_flags_forbidden_terms(self):
        task = {"required_any": ["pytest"], "forbidden": ["hardcode password"]}
        result = MODULE.evaluate_answer(task, "Use pytest; do not hardcode password.")
        self.assertIn("hardcode password", result["forbidden_terms_found"])
        self.assertFalse(result["heuristic_pass"])

    def test_heuristic_labels_itself_as_non_expert(self):
        result = MODULE.evaluate_answer({"required_any": ["test"]}, "Add a test.")
        self.assertIn("human review is required", result["warning"])


if __name__ == "__main__":
    unittest.main()
