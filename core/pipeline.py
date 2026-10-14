"""
Main orchestration pipeline.
Runs code review + security scan + learning + reporting.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from core.ollama_client import OllamaClient
from core.rag import MemoryStore
from core.permission_manager import PermissionManager, Action
from tools.git_tools import GitTools
from agents.code_reviewer import CodeReviewerAgent
from agents.security_scanner import SecurityScannerAgent
from agents.learner import LearnerAgent
from agents.reporter import ReporterAgent

logger = logging.getLogger("sentinel.pipeline")


class SentinelPipeline:
    def __init__(self):
        self.ollama = OllamaClient()
        self.memory = MemoryStore(ollama=self.ollama)
        self.permissions = PermissionManager()
        self.git = GitTools()

        self.reviewer = CodeReviewerAgent(ollama=self.ollama, memory=self.memory)
        self.security = SecurityScannerAgent(ollama=self.ollama, memory=self.memory)
        self.learner = LearnerAgent(ollama=self.ollama, memory=self.memory)
        self.reporter = ReporterAgent(ollama=self.ollama)

    def run_on_repo(self, repo_url: str, branch: str = "main", max_files: int = 8) -> str:
        """Full pipeline on a repository (read-only by default)."""

        logger.info(f"Starting pipeline on {repo_url}")

        # 1. Clone / update
        repo_path = self.git.clone_or_update(repo_url, branch=branch)
        repo_name = repo_path.name

        # 2. Decide which files to scan
        changed = self.git.get_changed_files(repo_path)
        if not changed:
            changed = self.git.list_python_files(repo_path, limit=max_files)

        changed = changed[:max_files]

        code_reviews = []
        security_findings = []

        for file_path in changed:
            content = self.git.get_file_content(repo_path, file_path)
            if not content or len(content) < 20:
                continue

            language = Path(file_path).suffix.lstrip(".") or "text"

            # Permission check (read is always allowed)
            if not self.permissions.can_perform(Action.READ_CODE):
                continue

            print(f"\n→ Reviewing {file_path} ...")

            # Code review
            try:
                review = self.reviewer.review_file(file_path, content, language=language)
                code_reviews.append(f"### {file_path}\n{review}")
                self.learner.learn_from_review(review, file_path, repo=repo_name)
            except Exception as e:
                logger.error(f"Review failed for {file_path}: {e}")
                code_reviews.append(f"### {file_path}\nError: {e}")

            # Security scan
            try:
                sec = self.security.scan_code(file_path, content, language=language)
                security_findings.append(f"### {file_path}\n{sec}")
            except Exception as e:
                logger.error(f"Security scan failed for {file_path}: {e}")

            # Learn from code
            try:
                self.learner.learn_from_code(file_path, content, repo=repo_name)
            except Exception as e:
                logger.error(f"Learning failed: {e}")

        # 3. Generate final report
        report = self.reporter.create_report(
            code_reviews=code_reviews,
            security_findings=security_findings,
            repo=repo_name,
        )

        # 4. Permission-aware output
        if self.permissions.can_perform(Action.CREATE_REPORT):
            print("\n" + "=" * 70)
            print(report)
            print("=" * 70)
        else:
            msg = self.permissions.request_approval(
                Action.CREATE_REPORT,
                f"Generate and show report for {repo_name}",
            )
            print(msg)

        return report

    def run_on_local_file(self, file_path: str) -> str:
        """Quick single file pipeline."""
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="ignore")
        language = path.suffix.lstrip(".") or "text"

        review = self.reviewer.review_file(str(path), content, language)
        security = self.security.scan_code(str(path), content, language)

        self.learner.learn_from_code(str(path), content)
        self.learner.learn_from_review(review, str(path))

        report = self.reporter.create_report(
            code_reviews=[review],
            security_findings=[security],
            repo="local",
        )
        return report
