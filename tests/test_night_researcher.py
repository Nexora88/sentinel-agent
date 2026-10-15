import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from agents.night_researcher import NightResearcher


class NightResearcherLocalCheckTests(unittest.TestCase):
    def make_researcher(self, directory):
        researcher = NightResearcher.__new__(NightResearcher)
        researcher.project_root = Path(directory)
        return researcher

    @patch("agents.night_researcher.subprocess.run")
    def test_checks_run_without_shell_and_have_timeout(self, run):
        run.side_effect = [
            Mock(returncode=0, stdout="compile ok", stderr=""),
            Mock(returncode=0, stdout="tests ok", stderr=""),
        ]
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SEKA_NIGHT_RUN_TESTS": "true"}):
            result = self.make_researcher(directory)._run_local_checks()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            self.assertNotIn("shell", call.kwargs)
            self.assertFalse(call.kwargs["check"])
            self.assertGreater(call.kwargs["timeout"], 0)

    @patch("agents.night_researcher.subprocess.run")
    def test_local_checks_can_be_disabled(self, run):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"SEKA_NIGHT_RUN_TESTS": "false"}):
            result = self.make_researcher(directory)._run_local_checks()
        self.assertEqual(result["status"], "disabled")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
