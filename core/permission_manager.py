"""
Permission Manager
Agents can only perform write actions after explicit approval.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from core.config import settings


class Action(str, Enum):
    READ_CODE = "read_code"
    RUN_STATIC_ANALYSIS = "run_static_analysis"
    CREATE_REPORT = "create_report"
    OPEN_GITHUB_ISSUE = "open_github_issue"
    CREATE_PULL_REQUEST = "create_pull_request"
    COMMIT_CHANGES = "commit_changes"
    PUSH_TO_REMOTE = "push_to_remote"
    MODIFY_FILES = "modify_files"
    SEND_NOTIFICATION = "send_notification"
    SCAN_WEBSITE = "scan_website"


class PermissionManager:
    def __init__(self):
        self.require_approval = settings.require_approval
        self.rules = settings.permissions.get("actions", {})
        self.pending_approvals: List[Dict] = []

    def can_perform(self, action: Action | str) -> bool:
        """Check if an action is allowed without approval."""
        action_key = action.value if isinstance(action, Action) else action
        rule = self.rules.get(action_key, "needs_approval")

        if rule == "allowed":
            return True
        if rule == "needs_approval":
            return not self.require_approval
        return False

    def request_approval(self, action: Action | str, details: str, context: Optional[dict] = None) -> str:
        """Create an approval request. Returns a message for the human."""
        action_key = action.value if isinstance(action, Action) else action

        request = {
            "action": action_key,
            "details": details,
            "context": context or {},
            "status": "pending",
        }
        self.pending_approvals.append(request)

        return (
            f"⚠️  APPROVAL REQUIRED\n"
            f"Action : {action_key}\n"
            f"Details: {details}\n"
            f"Status : Waiting for your explicit approval.\n"
            f"(Agents will never perform write / push actions without permission.)"
        )

    def list_pending(self) -> List[Dict]:
        return [r for r in self.pending_approvals if r["status"] == "pending"]

    def approve(self, index: int = 0) -> bool:
        pending = self.list_pending()
        if 0 <= index < len(pending):
            pending[index]["status"] = "approved"
            return True
        return False

    def reject(self, index: int = 0) -> bool:
        pending = self.list_pending()
        if 0 <= index < len(pending):
            pending[index]["status"] = "rejected"
            return True
        return False
