"""
GitHub integration for Sentinel.
Uses personal access token. All write operations go through PermissionManager.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any, Dict, List, Optional

import requests

from core.permission_manager import PermissionManager, Action

logger = logging.getLogger("sentinel.github")


class GitHubClient:
    """Authenticated GitHub operations."""

    def __init__(self, token: Optional[str] = None, permissions: Optional[PermissionManager] = None):
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        self.permissions = permissions or PermissionManager()
        self.api = "https://api.github.com"
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            })

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        r = self.session.get(f"{self.api}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict) -> Any:
        r = self.session.post(f"{self.api}{path}", json=data, timeout=30)
        r.raise_for_status()
        return r.json()

    def _put(self, path: str, data: dict) -> Any:
        r = self.session.put(f"{self.api}{path}", json=data, timeout=30)
        r.raise_for_status()
        return r.json()

    def me(self) -> Dict:
        if not self.enabled:
            return {"error": "GITHUB_TOKEN not set"}
        return self._get("/user")

    def list_repos(self, per_page: int = 30) -> List[Dict]:
        if not self.enabled:
            return []
        data = self._get("/user/repos", {"per_page": per_page, "sort": "updated"})
        return [
            {
                "name": r["name"],
                "full_name": r["full_name"],
                "private": r["private"],
                "url": r["html_url"],
                "description": r.get("description") or "",
                "language": r.get("language"),
                "updated_at": r.get("updated_at"),
            }
            for r in data
        ]

    def get_file(self, owner: str, repo: str, path: str, ref: str = "main") -> Dict:
        data = self._get(f"/repos/{owner}/{repo}/contents/{path}", {"ref": ref})
        if isinstance(data, list):
            return {"type": "dir", "entries": data}
        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
        return {
            "type": "file",
            "path": data["path"],
            "sha": data["sha"],
            "content": content,
            "size": data.get("size"),
        }

    def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
        sha: Optional[str] = None,
    ) -> str:
        """Write a file and commit. Requires MODIFY_FILES + PUSH permission."""
        if not self.permissions.can_perform(Action.MODIFY_FILES):
            return self.permissions.request_approval(
                Action.MODIFY_FILES,
                f"GitHub write: {owner}/{repo}/{path}\nCommit: {message}",
                context={"owner": owner, "repo": repo, "path": path, "preview": content[:400]},
            )

        if not self.permissions.can_perform(Action.PUSH_TO_REMOTE):
            return self.permissions.request_approval(
                Action.PUSH_TO_REMOTE,
                f"Push to {owner}/{repo} branch {branch}: {message}",
            )

        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        try:
            result = self._put(f"/repos/{owner}/{repo}/contents/{path}", payload)
            return f"✅ GitHub'a yazıldı: {owner}/{repo}/{path} → {result.get('commit', {}).get('html_url', '')}"
        except Exception as e:
            logger.error(f"GitHub write failed: {e}")
            return f"❌ GitHub yazma hatası: {e}"

    def create_issue(self, owner: str, repo: str, title: str, body: str = "") -> str:
        """Create an issue only when the configured policy explicitly permits it."""
        if not self.enabled:
            return "❌ GitHub token tanımlı değil."
        if not self.permissions.can_perform(Action.OPEN_GITHUB_ISSUE):
            return self.permissions.request_approval(
                Action.OPEN_GITHUB_ISSUE,
                f"GitHub issue: {owner}/{repo} — {title}",
                context={"owner": owner, "repo": repo, "title": title[:200], "body": body[:20000]},
            )
        try:
            result = self._post(f"/repos/{owner}/{repo}/issues", {"title": title, "body": body})
            return f"✅ Issue açıldı: {result.get('html_url')}"
        except Exception as e:
            logger.error("GitHub issue creation failed: %s", type(e).__name__)
            return "❌ Issue oluşturulamadı; hata ayrıntıları güvenlik için gizlendi."

    def execute_approved_request(self, request: Dict) -> str:
        """Execute only narrowly supported GitHub actions from a saved approval."""
        if not self.enabled:
            raise RuntimeError("GITHUB_TOKEN tanımlı değil; işlem yürütülmedi.")
        if request.get("status") != "executing":
            raise ValueError("GitHub işlemi yürütülmeden önce onaylı istek tek seferlik olarak sahiplenilmelidir.")
        action = request.get("action")
        context = request.get("context") or {}
        owner = str(context.get("owner", ""))
        repo = str(context.get("repo", ""))
        title = str(context.get("title", "")).strip()
        if not owner.isalnum() or not repo.replace("-", "").replace("_", "").isalnum():
            raise ValueError("GitHub depo kimliği geçersiz.")
        if not title or len(title) > 200:
            raise ValueError("Başlık boş veya çok uzun.")
        if action == Action.OPEN_GITHUB_ISSUE.value:
            body = str(context.get("body", ""))[:20000]
            result = self._post(f"/repos/{owner}/{repo}/issues", {"title": title, "body": body})
            return f"Issue oluşturuldu: {result.get('html_url', '')}"
        if action == Action.CREATE_PULL_REQUEST.value:
            head = str(context.get("head", "")).strip()
            base = str(context.get("base", "main")).strip()
            body = str(context.get("body", ""))[:20000]
            if not head or not base or len(head) > 250 or len(base) > 250:
                raise ValueError("PR dal bilgileri geçersiz.")
            result = self._post(
                f"/repos/{owner}/{repo}/pulls",
                {"title": title, "head": head, "base": base, "body": body},
            )
            return f"PR oluşturuldu: {result.get('html_url', '')}"
        raise ValueError("Bu işlem türü güvenli yürütücü tarafından desteklenmiyor; yalnızca onay kaydedildi.")

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
    ) -> str:
        if not self.permissions.can_perform(Action.CREATE_PULL_REQUEST):
            return self.permissions.request_approval(
                Action.CREATE_PULL_REQUEST,
                f"PR: {owner}/{repo} {head} → {base}: {title}",
                context={"owner": owner, "repo": repo, "title": title[:200], "head": head, "base": base, "body": body[:20000]},
            )
        try:
            result = self._post(
                f"/repos/{owner}/{repo}/pulls",
                {"title": title, "head": head, "base": base, "body": body},
            )
            return f"✅ PR açıldı: {result.get('html_url')}"
        except Exception as e:
            return f"❌ PR hatası: {e}"
