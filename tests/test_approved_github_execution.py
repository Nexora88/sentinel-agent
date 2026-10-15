import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from core.permission_manager import Action, PermissionManager
from tools.github_client import GitHubClient


class ApprovedGitHubExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.manager = PermissionManager(store_path=str(Path(self.tempdir.name) / "approvals.json"))
        self.client = GitHubClient(token="test-token", permissions=self.manager)
        self.client._post = Mock(return_value={"html_url": "https://github.com/example/project/issues/1"})

    def tearDown(self):
        self.tempdir.cleanup()

    def test_approved_issue_executes_once_and_records_result(self):
        notice = self.manager.request_approval(
            Action.OPEN_GITHUB_ISSUE,
            "Create test issue",
            {"owner": "example", "repo": "project", "title": "Test issue", "body": "No private data"},
        )
        request_id = notice.split("Request ID: ", 1)[1].splitlines()[0]
        self.assertTrue(self.manager.approve(request_id))
        self.assertTrue(self.manager.begin_execution(request_id))
        request = self.manager.get_request(request_id)
        result = self.client.execute_approved_request(request)
        self.assertIn("https://github.com/example/project/issues/1", result)
        self.assertTrue(self.manager.finish_execution(request_id, True, result))
        self.assertFalse(self.manager.begin_execution(request_id))
        self.client._post.assert_called_once_with(
            "/repos/example/project/issues",
            {"title": "Test issue", "body": "No private data"},
        )
        self.assertEqual(self.manager.get_request(request_id)["status"], "executed")

    def test_file_change_requires_two_approvals_before_remote_write(self):
        notice = self.client.create_or_update_file(
            "example", "project", "docs/guide.md", "# Local draft", "Add guide", "feature/guide"
        )
        first_id = notice.split("Request ID: ", 1)[1].splitlines()[0]
        self.assertTrue(self.manager.approve(first_id))
        self.assertTrue(self.manager.begin_execution(first_id))
        first = self.manager.get_request(first_id)
        result = self.client.execute_approved_request(first)
        self.assertIn(Action.PUSH_TO_REMOTE.value, result)
        self.assertTrue(self.manager.finish_execution(first_id, True, result, final_status="staged"))
        self.client._put = Mock(return_value={"commit": {"html_url": "https://github.com/example/project/commit/abc"}})
        second = next(item for item in self.manager.list_actionable() if item["action"] == Action.PUSH_TO_REMOTE.value)
        self.assertEqual(second["context"]["content"], "# Local draft")
        self.assertFalse(self.client._put.called)
        self.assertTrue(self.manager.approve(second["id"]))
        self.assertTrue(self.manager.begin_execution(second["id"]))
        claimed = self.manager.get_request(second["id"])
        result = self.client.execute_approved_request(claimed)
        self.assertIn("/commit/abc", result)
        self.assertTrue(self.manager.finish_execution(second["id"], True, result))
        self.client._put.assert_called_once()

    def test_unknown_action_never_dispatches(self):
        request = {
            "status": "executing",
            "action": "push_to_remote",
            "context": {"owner": "example", "repo": "project", "title": "unexpected"},
        }
        with self.assertRaises(ValueError):
            self.client.execute_approved_request(request)
        self.client._post.assert_not_called()

    def test_unclaimed_approval_is_rejected(self):
        request = {
            "status": "approved",
            "action": Action.OPEN_GITHUB_ISSUE.value,
            "context": {"owner": "example", "repo": "project", "title": "test"},
        }
        with self.assertRaises(ValueError):
            self.client.execute_approved_request(request)
        self.client._post.assert_not_called()

    def test_invalid_repository_name_is_rejected(self):
        request = {
            "status": "executing",
            "action": Action.OPEN_GITHUB_ISSUE.value,
            "context": {"owner": "example", "repo": "../secret", "title": "test"},
        }
        with self.assertRaises(ValueError):
            self.client.execute_approved_request(request)
        self.client._post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
