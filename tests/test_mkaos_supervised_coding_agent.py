import tempfile
import unittest
from pathlib import Path

from tools.mkaos_supervised_coding_agent import validate


class SupervisedCodingAgentInputTests(unittest.TestCase):
    def test_rejects_oversized_patch_before_running_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            patch = root / "proposal.patch"
            patch.write_bytes(b"x" * (5_000_001))
            with self.assertRaisesRegex(ValueError, "5 MB"):
                validate(root, patch, "HEAD", root / "report.json")

    def test_rejects_option_injection_in_base_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            patch = root / "proposal.patch"
            patch.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid base ref"):
                validate(root, patch, "--upload-pack=evil", root / "report.json")


if __name__ == "__main__":
    unittest.main()
