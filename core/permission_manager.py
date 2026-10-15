"""
Permission Manager
Write, push and external side effects require explicit human approval.
Approval requests are persisted locally with stable IDs and atomic writes.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
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
    def __init__(self, store_path: str = "./memory/approvals.json"):
        self.require_approval = settings.require_approval
        self.rules = settings.permissions.get("actions", {})
        self.store_path = Path(store_path)
        self._lock = threading.RLock()
        self.pending_approvals: List[Dict] = self._load()

    def _load(self) -> List[Dict]:
        if not self.store_path.exists():
            return []
        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
            if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
                raise ValueError("approval store must be a JSON list")
            # Legacy records without IDs cannot be approved by positional index.
            for item in data:
                item.setdefault("id", uuid.uuid4().hex)
                item.setdefault("status", "pending")
            return data
        except Exception as exc:
            # Never overwrite a damaged approval history automatically.
            raise RuntimeError(
                f"Approval store is unreadable; preserve and recover {self.store_path} before restarting."
            ) from exc

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        # Keep a bounded audit trail; pending requests are never pruned.
        if len(self.pending_approvals) > 5000:
            completed = [r for r in self.pending_approvals if r.get("status") != "pending"]
            keep_completed = set(id(r) for r in completed[-4500:])
            self.pending_approvals = [
                r for r in self.pending_approvals
                if r.get("status") == "pending" or id(r) in keep_completed
            ]
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=str(self.store_path.parent),
                prefix=".approvals-", suffix=".tmp", delete=False
            ) as temp:
                json.dump(self.pending_approvals, temp, ensure_ascii=False, indent=2, default=str)
                temp.flush()
                os.fsync(temp.fileno())
                temp_name = temp.name
            try:
                os.chmod(temp_name, 0o600)
            except OSError:
                pass
            os.replace(temp_name, self.store_path)
            try:
                os.chmod(self.store_path, 0o600)
            except OSError:
                pass
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)

    def can_perform(self, action: Action | str) -> bool:
        """Return true only for explicitly allowed low-risk actions."""
        action_key = action.value if isinstance(action, Action) else str(action)
        return self.rules.get(action_key, "needs_approval") == "allowed"

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
            self._save()
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

    def get_request(self, request_id: str) -> Optional[Dict]:
        with self._lock:
            for request in self.pending_approvals:
                if request.get("id") == request_id:
                    return dict(request)
        return None

    def list_actionable(self) -> List[Dict]:
        """Show pending requests and approved requests awaiting explicit execution."""
        with self._lock:
            return [
                dict(r) for r in self.pending_approvals
                if r.get("status") in {"pending", "approved"}
            ]

    def begin_execution(self, request_id: str) -> bool:
        """Claim an approved request once before performing an external side effect."""
        with self._lock:
            for request in self.pending_approvals:
                if request.get("id") == request_id and request.get("status") == "approved":
                    request["status"] = "executing"
                    request["execution_started_at"] = datetime.now(timezone.utc).isoformat()
                    self._save()
                    return True
        return False

    def finish_execution(self, request_id: str, success: bool, result: str) -> bool:
        with self._lock:
            for request in self.pending_approvals:
                if request.get("id") == request_id and request.get("status") == "executing":
                    request["status"] = "executed" if success else "execution_failed"
                    request["execution_result"] = str(result)[:1000]
                    request["execution_finished_at"] = datetime.now(timezone.utc).isoformat()
                    self._save()
                    return True
        return False

    def approve(self, request_id: str = "") -> bool:
        """Approve a specific request by stable ID; positional indexes fail closed."""
        if not isinstance(request_id, str) or not request_id:
            return False
        with self._lock:
            for request in self.pending_approvals:
                if request["id"] == request_id and request["status"] == "pending":
                    request["status"] = "approved"
                    request["approved_at"] = datetime.now(timezone.utc).isoformat()
                    self._save()
                    return True
        return False

    def reject(self, request_id: str = "") -> bool:
        """Reject a specific request by stable ID; positional indexes fail closed."""
        if not isinstance(request_id, str) or not request_id:
            return False
        with self._lock:
            for request in self.pending_approvals:
                if request["id"] == request_id and request["status"] == "pending":
                    request["status"] = "rejected"
                    request["rejected_at"] = datetime.now(timezone.utc).isoformat()
                    self._save()
                    return True
        return False
