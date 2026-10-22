import unittest

from tools.ci_failure_report import build_report, redact


class CIFailureReportTests(unittest.TestCase):
    def test_redacts_common_tokens_and_password_values(self):
        source = (
            "Authorization: Bearer abc.def.ghi "
            "github_pat_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456 "
            "password=very-secret-value"
        )
        safe = redact(source)
        self.assertNotIn("abc.def.ghi", safe)
        self.assertNotIn("github_pat_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456", safe)
        self.assertNotIn("very-secret-value", safe)
        self.assertIn("[REDACTED]", safe)

    def test_report_records_commit_and_safe_boundaries(self):
        report = build_report("12345", "deadbeef", "FAILED test_sample.py")
        self.assertIn("Workflow run ID: 12345", report)
        self.assertIn("Source commit: deadbeef", report)
        self.assertIn("network-restricted environment", report)
        self.assertIn("merge and deployment", report)
        self.assertIn("FAILED test_sample.py", report)
        self.assertIn("Source checkout: not performed", report)

    def test_large_log_is_bounded(self):
        report = build_report("1", "abc", "x" * 300_000)
        self.assertIn("Log truncated: yes", report)
        self.assertLess(len(report), 260_000)


if __name__ == "__main__":
    unittest.main()
