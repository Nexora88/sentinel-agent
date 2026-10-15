"""
Permission Manager
Write, push and external side effects require explicit human approval.
Approval IDs are stable within the process; requests are not silently auto-approved.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
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
        self._lock = threading.RLock()

    def can_perform(self, action: Action | str) -> bool:
        """Return true only for explicitly allowed low-risk actions."""
        action_key = action.value if isinstance(action, Action) else str(action)
        rule = self.rules.get(action_key, "needs_approval")
        if rule == "allowed":
            return True
        # Unknown or approval-required actions are denied unless an explicit
        # approval flow is used; configuration must never silently bypass it.
        return False

    def request_approval(
        self, action: Action | str, details: str, context: Optional[dict] = None
    ) -> str:
        action_key = action.value if isinstance(action, Action) else str(action)
        request_id = uuid.uuid4().hex
        request = {
            "id": request_id,
            "action": action_key,
            "details": str(details)[:4000],
            "context": context or {},
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self.pending_approvals.append(request)
        return (
            f"⚠️ APPROVAL REQUIRED\n"
            f"Request ID: {request_id}\n"
            f"Action: {action_key}\n"
            f"Details: {request['details']}\n"
            "Status: Waiting for explicit owner approval. "
            "No write/push action has been performed."
        )

    def list_pending(self) -> List[Dict]:
        with self._lock:
            return [dict(r) for r in self.pending_approvals if r["status"] == "pending"]

    def approve(self, request_id: str = "") -> bool:
        """Approve a specific request by stable ID; legacy numeric indexes fail closed."""
        if not isinstance(request_id, str) or not request_id:
            return False
        with self._lock:
            for request in self.pending_approvals:
                if request["id"] == request_id and request["status"] == "pending":
                    request["status"] = "approved"
                    request["approved_at"] = datetime.now(timezone.utc).isoformat()
                    return True
        return False

    def reject(self, request_id: str = "") -> bool:
        """Reject a specific request by stable ID; legacy numeric indexes fail closed."""
        if not isinstance(request_id, str) or not request_id:
            return False
        with self._lock:
            for request in self.pending_approvals:
                if request["id"] == request_id and request["status"] == "pending":
                    request["status"] = "rejected"
                    request["rejected_at"] = datetime.now(timezone.utc).isoformat()
                    return True
        return False
