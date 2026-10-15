import unittest
from core.reasoning_engine import LocalReasoningEngine


class FakeModel:
    model_name = "local-test-model"

    def __init__(self):
        self.calls = []

    def chat(self, prompt, system=None, temperature=None):
        self.calls.append((prompt, system, temperature))
        return f"response-{len(self.calls)}"


class ReasoningEngineTests(unittest.TestCase):
    def test_three_pass_flow_returns_summary_without_side_effects(self):
        model = FakeModel()
        engine = LocalReasoningEngine(model, max_passes=3, verifier=lambda draft: "local check")
        result = engine.run("Review a patch", context="untrusted context")
        self.assertEqual(len(model.calls), 3)
        self.assertEqual(result.answer, "response-3")
        self.assertEqual(result.passes, 3)
        self.assertFalse(result.side_effects_performed)
        self.assertIn("no actions executed", result.plan_summary.lower())

    def test_pass_count_is_bounded(self):
        model = FakeModel()
        result = LocalReasoningEngine(model, max_passes=99).run("A task")
        self.assertEqual(len(model.calls), 3)
        self.assertEqual(result.passes, 3)

    def test_single_pass_does_not_claim_critique(self):
        model = FakeModel()
        result = LocalReasoningEngine(model, max_passes=1).run("A task")
        self.assertEqual(len(model.calls), 1)
        self.assertIn("Not run", result.critique_summary)

    def test_empty_task_rejected(self):
        with self.assertRaises(ValueError):
            LocalReasoningEngine(FakeModel()).run("  ")


if __name__ == "__main__":
    unittest.main()
