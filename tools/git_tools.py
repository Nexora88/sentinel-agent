"""
Git tools for Sentinel Agent.
Safe read-only operations by default.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from git import Repo, GitCommandError


class GitTools:
    def __init__(self, work_dir: Optional[str] = None):
        self.work_dir = Path(work_dir or tempfile.mkdtemp(prefix="sentinel_"))
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def clone_or_update(self, repo_url: str, branch: str = "main") -> Path:
        """Clone a repository or pull latest changes."""
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        target = self.work_dir / repo_name

        if target.exists():
            try:
                repo = Repo(target)
                repo.remotes.origin.pull()
                return target
            except Exception:
                # fallback to fresh clone
                import shutil
                shutil.rmtree(target, ignore_errors=True)

        Repo.clone_from(repo_url, target, branch=branch)
        return target

    def get_changed_files(self, repo_path: Path, base: str = "HEAD~1") -> List[str]:
        """Return list of changed files compared to base."""
        repo = Repo(repo_path)
        try:
            diff = repo.git.diff(base, name_only=True)
            return [f for f in diff.splitlines() if f.strip()]
        except GitCommandError:
            # first commit or empty
            return [str(p.relative_to(repo_path)) for p in repo_path.rglob("*") if p.is_file()]

    def get_file_content(self, repo_path: Path, file_path: str) -> str:
        full = repo_path / file_path
        if not full.exists():
            return ""
        return full.read_text(encoding="utf-8", errors="ignore")

    def get_diff(self, repo_path: Path, base: str = "HEAD~1") -> str:
        repo = Repo(repo_path)
        try:
            return repo.git.diff(base)
        except GitCommandError:
            return ""

    def list_python_files(self, repo_path: Path, limit: int = 30) -> List[str]:
        """List Python files (useful for first full scan)."""
        files = []
        for p in repo_path.rglob("*.py"):
            if any(x in p.parts for x in [".git", "venv", ".venv", "__pycache__", "node_modules"]):
                continue
            files.append(str(p.relative_to(repo_path)))
            if len(files) >= limit:
                break
        return files
