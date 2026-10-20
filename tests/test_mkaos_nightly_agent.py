import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.mkaos_nightly_agent import run_audit


class NightWatchAgentTests(unittest.TestCase):
    def test_rejects_parent_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "allowlist.json"
            config.write_text(json.dumps({
                "schema_version": 1,
                "projects": [{"id": "escape", "path": "../outside", "enabled": True,
                              "checks": ["python_tests"]}]
            }), encoding="utf-8")
            report = run_audit(config, root)
            self.assertEqual(report["projects"][0]["status"], "blocked")
            self.assertEqual(report["overall_status"], "failed")

    def test_skips_disabled_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "allowlist.json"
            config.write_text(json.dumps({
                "schema_version": 1,
                "projects": [{"id": "disabled", "path": ".", "enabled": False,
                              "checks": ["python_tests"]}]
            }), encoding="utf-8")
            report = run_audit(config, root)
            self.assertEqual(report["projects"], [])
            self.assertEqual(report["overall_status"], "completed")

    def test_rejects_unknown_check_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "allowlist.json"
            config.write_text(json.dumps({
                "schema_version": 1,
                "projects": [{"id": "project", "path": ".", "enabled": True,
                              "checks": ["arbitrary_shell_command"]}]
            }), encoding="utf-8")
            report = run_audit(config, root)
            self.assertEqual(report["projects"][0]["status"], "failed")
            self.assertEqual(report["projects"][0]["invalid_checks"],
                             ["arbitrary_shell_command"])


if __name__ == "__main__":
    unittest.main()
