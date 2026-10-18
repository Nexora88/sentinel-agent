import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "mkaos_scale_planner", ROOT / "tools" / "plan_mkaos_scale.py"
)
PLANNER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PLANNER)


class MkaosScalePlannerTests(unittest.TestCase):
    def test_default_target_rounds_to_a_measured_architecture_count(self):
        target = 50_000_000_000
        width = 10240
        actual = PLANNER.parameter_count(257, width, 48, 80, 10, int(width * 2.6667))
        self.assertLess(abs(actual - target), target * 0.05)

    def test_estimator_rejects_invalid_architecture(self):
        with self.assertRaises(ValueError):
            PLANNER.parameter_count(257, 1001, 4, 8, 2, 2048)


if __name__ == "__main__":
    unittest.main()

