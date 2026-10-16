"""Unit tests for the deterministic low-memory MKAOS training schedule."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "train_mkaos_from_scratch.py"
SPEC = importlib.util.spec_from_file_location("mkaos_training_schedule", SCRIPT)
assert SPEC and SPEC.loader
TRAINER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRAINER)


class TrainingScheduleTests(unittest.TestCase):
    def test_warmup_increases_linearly(self):
        self.assertAlmostEqual(TRAINER.learning_rate_for_step(0.1, 1, 10, 2, 0.1), 0.05)
        self.assertAlmostEqual(TRAINER.learning_rate_for_step(0.1, 2, 10, 2, 0.1), 0.1)

    def test_cosine_decay_starts_at_base_and_finishes_at_floor(self):
        self.assertAlmostEqual(TRAINER.learning_rate_for_step(0.01, 1, 5, 0, 0.2), 0.01)
        self.assertAlmostEqual(TRAINER.learning_rate_for_step(0.01, 5, 5, 0, 0.2), 0.002)

    def test_schedule_is_non_increasing_after_warmup(self):
        rates = [TRAINER.learning_rate_for_step(1.0, step, 12, 3, 0.1) for step in range(4, 13)]
        self.assertEqual(rates, sorted(rates, reverse=True))
        self.assertTrue(all(0.1 <= rate <= 1.0 for rate in rates))

    def test_invalid_schedule_inputs_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "step must"):
            TRAINER.learning_rate_for_step(0.1, 0, 10)
        with self.assertRaisesRegex(ValueError, "warmup_steps"):
            TRAINER.learning_rate_for_step(0.1, 1, 10, 11)
        with self.assertRaisesRegex(ValueError, "min_learning_rate_ratio"):
            TRAINER.learning_rate_for_step(0.1, 1, 10, 0, 0)


if __name__ == "__main__":
    unittest.main()
