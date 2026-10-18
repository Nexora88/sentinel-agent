import importlib.util
import json
import subprocess
import sys
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "mkaos_scale_planner", ROOT / "tools" / "plan_mkaos_scale.py"
)
PLANNER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PLANNER)


class MkaosScalePlannerTests(unittest.TestCase):
    def test_10b_target_matches_checked_in_profile_exactly(self):
        import json

        profile = json.loads((ROOT / "configs" / "mkaos" / "train-10b.json").read_text(encoding="utf-8"))
        model = profile["model"]
        actual = PLANNER.parameter_count(
            257, model["hidden_size"], model["layers"], model["heads"],
            model["kv_heads"], model["intermediate_size"],
        )
        self.assertEqual(actual, 10_068_848_640)
        self.assertEqual(actual, profile["expected_parameter_count"])
        self.assertTrue(profile["execution_status"]["planning_only"])
        self.assertTrue(profile["execution_status"]["blocked"])
        self.assertFalse(profile["governance"]["default_training_enabled"])

    def test_training_runner_rejects_blocked_10b_profile(self):
        import json
        from tools.train_mkaos_profile import load_profile

        profile = json.loads((ROOT / "configs" / "mkaos" / "train-10b.json").read_text(encoding="utf-8"))
        actual = PLANNER.parameter_count(
            257, profile["model"]["hidden_size"], profile["model"]["layers"],
            profile["model"]["heads"], profile["model"]["kv_heads"],
            profile["model"]["intermediate_size"],
        )
        profile["expected_parameter_count"] = actual
        with patch("pathlib.Path.read_text", return_value=json.dumps(profile)):
            with self.assertRaisesRegex(ValueError, "planning-only and blocked"):
                load_profile(ROOT / "configs" / "mkaos" / "train-10b.json")

    def test_default_scale_target_is_10b(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "plan_mkaos_scale.py")],
            check=True, capture_output=True, text=True,
        )
        report = json.loads(result.stdout)
        self.assertEqual(report["architecture"]["profile"], "mkaos-10b-scratch-target")
        self.assertEqual(report["exact_parameter_count_for_current_implementation"], 10_068_848_640)
        self.assertIn("training was not started", report["mode"])

    def test_estimator_rejects_invalid_architecture(self):
        with self.assertRaises(ValueError):
            PLANNER.parameter_count(257, 1001, 4, 8, 2, 2048)


if __name__ == "__main__":
    unittest.main()

