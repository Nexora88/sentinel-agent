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
        """Stage a file change; separate owner approvals are required for editing and remote push."""
        if not self.enabled:
            return "GitHub token tanımlı değil; hiçbir işlem yapılmadı."
        if len(content.encode("utf-8")) > 100_000:
            return "Dosya 100 KB sınırını aşıyor; küçük parçalara böl ve tekrar dene."
        return self.permissions.request_approval(
            Action.MODIFY_FILES,
            f"GitHub dosya değişikliği: {owner}/{repo}/{path}\nDal: {branch}\nCommit: {message}\nİçerik: {len(content)} karakter",
            context={
                "owner": owner, "repo": repo, "path": path, "content": content,
                "message": message[:200], "branch": branch, "sha": sha,
            },
        )

    def create_issue(self, owner: str, repo: str, title: str, body: str = "") -> str:
        """GitHub issues always require a durable explicit owner approval."""
        if not self.enabled:
            return "GitHub token tanımlı değil; hiçbir işlem yapılmadı."
        if not title.strip() or len(title) > 200 or len(body) > 20000:
            return "Issue başlığı/gövdesi sınırları aşıyor; hiçbir işlem yapılmadı."
        return self.permissions.request_approval(
            Action.OPEN_GITHUB_ISSUE,
            f"GitHub issue: {owner}/{repo} — {title}",
            context={"owner": owner, "repo": repo, "title": title.strip(), "body": body},
        )

    def execute_approved_request(self, request: Dict) -> str:
        """Execute only an explicitly approved, atomically claimed GitHub action."""
        if not self.enabled:
            raise RuntimeError("GITHUB_TOKEN tanımlı değil; işlem yürütülmedi.")
        if request.get("status") != "executing":
            raise ValueError("İşlem önce onaylanmalı ve tek seferlik yürütme kilidi alınmalı.")
        action = request.get("action")
        context = request.get("context") or {}
        owner = str(context.get("owner", ""))
        repo = str(context.get("repo", ""))
        if not owner.replace("-", "").isalnum() or not repo.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError("GitHub depo kimliği geçersiz.")

        if action in {Action.OPEN_GITHUB_ISSUE.value, Action.CREATE_PULL_REQUEST.value}:
            title = str(context.get("title", "")).strip()
            if not title or len(title) > 200:
                raise ValueError("Başlık boş veya çok uzun.")
            body = str(context.get("body", ""))[:20000]
            if action == Action.OPEN_GITHUB_ISSUE.value:
                result = self._post(f"/repos/{owner}/{repo}/issues", {"title": title, "body": body})
                return f"Issue oluşturuldu: {result.get('html_url', '')}"
            head = str(context.get("head", "")).strip()
            base = str(context.get("base", "main")).strip()
            if not head or not base or len(head) > 250 or len(base) > 250:
                raise ValueError("PR dal bilgileri geçersiz.")
            result = self._post(
                f"/repos/{owner}/{repo}/pulls",
                {"title": title, "head": head, "base": base, "body": body},
            )
            return f"PR oluşturuldu: {result.get('html_url', '')}"

        if action in {Action.MODIFY_FILES.value, Action.PUSH_TO_REMOTE.value}:
            path = str(context.get("path", ""))
            parts = path.split("/")
            branch = str(context.get("branch", "main"))
            message = str(context.get("message", "")).strip()
            content = context.get("content")
            sha = context.get("sha")
            if (not path or path.startswith("/") or "\\" in path or any(p in {"", ".", ".."} for p in parts)
                    or len(path) > 500):
                raise ValueError("GitHub dosya yolu geçersiz.")
            if (not branch or len(branch) > 250 or ".." in branch or branch.startswith("/")
                    or branch.endswith("/") or any(c.isspace() for c in branch)):
                raise ValueError("Git dalı geçersiz.")
            if not message or len(message) > 200 or not isinstance(content, str) or len(content.encode("utf-8")) > 100000:
                raise ValueError("Commit metni veya dosya içeriği sınırları geçersiz.")
            if sha is not None and (not isinstance(sha, str) or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha.lower())):
                raise ValueError("Dosya SHA değeri geçersiz.")
            if action == Action.MODIFY_FILES.value:
                # First approval only authorizes staging the intent; it does not contact GitHub.
                return self.permissions.request_approval(
                    Action.PUSH_TO_REMOTE,
                    f"İkinci onay gerekli: {owner}/{repo}/{path} dosyasını {branch} dalına yaz ve commit et.\nCommit: {message}",
                    context={
                        "owner": owner, "repo": repo, "path": path, "content": content,
                        "message": message, "branch": branch, "sha": sha,
                    },
                )
            payload = {
                "message": message,
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                "branch": branch,
            }
            if sha:
                payload["sha"] = sha
            from urllib.parse import quote
            result = self._put(f"/repos/{owner}/{repo}/contents/{quote(path, safe='/')}", payload)
            commit_url = result.get("commit", {}).get("html_url", "")
            return f"GitHub dosyası güncellendi: {owner}/{repo}/{path} → {commit_url}"

        raise ValueError("Bu işlem türü güvenli GitHub yürütücüsü tarafından desteklenmiyor.")

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
    ) -> str:
        """GitHub pull requests always require a durable explicit owner approval."""
        if not self.enabled:
            return "GitHub token tanımlı değil; hiçbir işlem yapılmadı."
        if not title.strip() or len(title) > 200 or len(body) > 20000:
            return "PR başlığı/gövdesi sınırları aşıyor; hiçbir işlem yapılmadı."
        return self.permissions.request_approval(
            Action.CREATE_PULL_REQUEST,
            f"PR: {owner}/{repo} {head} → {base}: {title}",
            context={"owner": owner, "repo": repo, "title": title.strip(), "head": head, "base": base, "body": body},
        )
