import tempfile
import unittest
from pathlib import Path

from tools.audit_dependencies import build_report


class DependencyAuditTests(unittest.TestCase):
    def test_reports_unpinned_dependencies_and_lock_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements.txt").write_text(
                "alpha==1.2.3\nbeta>=2.0\n", encoding="utf-8"
            )
            (root / "engine/mkaos-inference").mkdir(parents=True)
            (root / "engine/mkaos-inference/Cargo.toml").write_text(
                '[package]\nname="test"\nversion="0.1.0"\n'
                '[dependencies]\nserde_json = "1"\nfixed = "=2.3.4"\n',
                encoding="utf-8",
            )
            report = build_report(root)
            self.assertFalse(report["network_accessed"])
            self.assertEqual(report["dependency_count"], 4)
            self.assertEqual(report["pinned_count"], 2)
            self.assertEqual(report["unpinned_count"], 2)
            self.assertIn("engine/mkaos-inference/Cargo.lock", report["lockfile_gaps"])

    def test_does_not_claim_advisory_or_legal_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements.txt").write_text("", encoding="utf-8")
            report = build_report(root)
            self.assertFalse(report["advisory_database_checked"])
            self.assertFalse(report["legal_review_performed"])


if __name__ == "__main__":
    unittest.main()
