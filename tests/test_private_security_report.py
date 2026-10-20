import json
import tempfile
import unittest
from pathlib import Path

from core.location_data_adapters import Location, TrafficAdapter, WeatherAdapter
from tools.mkaos_private_security_report import write_private_report, sanitize


class PrivateSecurityReportTests(unittest.TestCase):
    def test_report_is_private_and_redacts_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_private_report(
                [{"rule": "token", "evidence": "ghp_" + "A" * 35, "source_excerpt": "private"}],
                Path(tmp) / "private.json",
            )
            report = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(report["visibility"], "private-local-owner-review")
            self.assertFalse(report["public_issue_created"])
            rendered = path.read_text(encoding="utf-8")
            self.assertNotIn("ghp_" + "A" * 35, rendered)
            self.assertNotIn('"private"', rendered)

    def test_secret_like_text_is_redacted(self):
        value = sanitize({"message": "AKIA" + "1234567890ABCDEF"})
        self.assertEqual(value["message"], "[REDACTED_SECRET]")


if __name__ == "__main__":
    unittest.main()
