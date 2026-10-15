import tempfile
import unittest
from pathlib import Path

from core.improvement_gate import ImprovementProposalError, ImprovementProposalStore, validate_candidate


class ImprovementGateTests(unittest.TestCase):
    def candidate(self):
        return {
            "title": "Add regression coverage",
            "rationale": "Protect a deterministic behavior with a test.",
            "files": ["core/example.py", "tests/test_example.py"],
            "patch": "--- a/core/example.py\n+++ b/core/example.py\n@@\n+def safe_example(): return True\n",
            "test_plan": ["python -m unittest tests.test_example"],
        }

    def test_create_and_approve_only_marks_for_human_review(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ImprovementProposalStore(directory)
            proposal = store.create(**self.candidate())
            self.assertEqual(proposal["status"], "pending_review")
            self.assertNotIn("patch", proposal)
            approved = store.approve_for_review(proposal["id"], "READY_FOR_HUMAN_CODE_REVIEW")
            self.assertEqual(approved["status"], "ready_for_human_review")
            self.assertEqual(approved["execution"], "never_auto_applied")
            stored = (Path(directory) / (proposal["id"] + ".json")).read_text(encoding="utf-8")
            self.assertIn("safe_example", stored)

    def test_rejects_path_traversal_and_secret_files(self):
        for target in ("../README.md", "core/../../secrets.txt", "core/.env", "tools/secrets.py", "/tmp/code.py"):
            with self.subTest(target=target):
                candidate = self.candidate()
                candidate["files"] = [target]
                with self.assertRaises(ImprovementProposalError):
                    validate_candidate(**candidate)

    def test_approval_requires_explicit_phrase_and_cannot_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ImprovementProposalStore(directory)
            proposal = store.create(**self.candidate())
            with self.assertRaises(ImprovementProposalError):
                store.approve_for_review(proposal["id"], "yes")
            store.approve_for_review(proposal["id"], "READY_FOR_HUMAN_CODE_REVIEW")
            with self.assertRaises(ImprovementProposalError):
                store.approve_for_review(proposal["id"], "READY_FOR_HUMAN_CODE_REVIEW")

    def test_patch_size_is_bounded(self):
        candidate = self.candidate()
        candidate["patch"] = "x" * 50001
        with self.assertRaises(ImprovementProposalError):
            validate_candidate(**candidate)


if __name__ == "__main__":
    unittest.main()
