"""
Main orchestration pipeline — full power.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from core.ollama_client import OllamaClient
from core.rag import MemoryStore
from core.personal_memory import PersonalMemory
from core.permission_manager import PermissionManager, Action
from tools.git_tools import GitTools
from tools.notifier import Notifier
from tools.code_writer import CodeWriter
from tools.website_scanner import WebsiteScanner
from tools.github_client import GitHubClient
from tools.finance_engine import FinanceEngine
from tools.image_gen import ImageGenerator
from agents.code_reviewer import CodeReviewerAgent
from agents.security_scanner import SecurityScannerAgent
from agents.learner import LearnerAgent
from agents.reporter import ReporterAgent
from agents.debugger import DebuggerAgent
from agents.personal_assistant import PersonalAssistant
from agents.knowledge_expander import KnowledgeExpander

logger = logging.getLogger("sentinel.pipeline")


class SentinelPipeline:
    def __init__(self):
        self.ollama = OllamaClient()
        self.memory = MemoryStore(ollama=self.ollama)
        self.personal_memory = PersonalMemory(ollama=self.ollama)
        self.permissions = PermissionManager()
        self.git = GitTools()
        self.notifier = Notifier()
        self.code_writer = CodeWriter(ollama=self.ollama, permissions=self.permissions)
        self.website_scanner = WebsiteScanner()

        # New major engines
        self.github = GitHubClient(permissions=self.permissions)
        self.finance = FinanceEngine(ollama=self.ollama)
        self.image_gen = ImageGenerator()

        self.reviewer = CodeReviewerAgent(ollama=self.ollama, memory=self.memory)
        self.security = SecurityScannerAgent(ollama=self.ollama, memory=self.memory)
        self.learner = LearnerAgent(ollama=self.ollama, memory=self.memory)
        self.reporter = ReporterAgent(ollama=self.ollama)
        self.debugger = DebuggerAgent(ollama=self.ollama, memory=self.memory)

        self.expander = KnowledgeExpander(ollama=self.ollama, memory=self.memory)

        self.assistant = PersonalAssistant(
            ollama=self.ollama,
            memory=self.personal_memory,
            permissions=self.permissions,
            pipeline=self,
        )

    def chat(self, message: str) -> str:
        return self.assistant.chat(message)

    def status(self) -> str:
        base = self.assistant.get_status()
        uni = self.expander.get_status()
        gh = "bağlı" if self.github.enabled else "token yok"
        return (
            f"{base}\n\n"
            f"🌌 Bilgi Evreni: {uni.get('total_pages', 0)} parça | {uni.get('total_runs', 0)} tur\n"
            f"🐙 GitHub: {gh}\n"
            f"📈 Finans motoru: aktif\n"
            f"🖼️ Görsel motoru: aktif"
        )

    def expand_knowledge(self, topic: Optional[str] = None) -> dict:
        if topic:
            self.expander.add_seed_topic(topic)
        return self.expander.expand_once(extra_topics=[topic] if topic else None)

    def run_on_repo(self, repo_url: str, branch: str = "main", max_files: int = 8) -> str:
        logger.info(f"Starting pipeline on {repo_url}")
        repo_path = self.git.clone_or_update(repo_url, branch=branch)
        repo_name = repo_path.name

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
            print(f"\n→ Reviewing {file_path} ...")
            try:
                review = self.reviewer.review_file(file_path, content, language=language)
                code_reviews.append(f"### {file_path}\n{review}")
                self.learner.learn_from_review(review, file_path, repo=repo_name)
            except Exception as e:
                logger.error(f"Review failed: {e}")
            try:
                sec = self.security.scan_code(file_path, content, language=language)
                security_findings.append(f"### {file_path}\n{sec}")
            except Exception as e:
                logger.error(f"Security failed: {e}")
            try:
                self.learner.learn_from_code(file_path, content, repo=repo_name)
            except Exception as e:
                logger.error(f"Learn failed: {e}")

        report = self.reporter.create_report(
            code_reviews=code_reviews,
            security_findings=security_findings,
            repo=repo_name,
        )
        self.notifier.notify(report, whatsapp=True)
        return report

    def run_on_local_file(self, file_path: str) -> str:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="ignore")
        language = path.suffix.lstrip(".") or "text"
        review = self.reviewer.review_file(str(path), content, language)
        security = self.security.scan_code(str(path), content, language)
        self.learner.learn_from_code(str(path), content)
        self.learner.learn_from_review(review, str(path))
        report = self.reporter.create_report(
            code_reviews=[review], security_findings=[security], repo="local"
        )
        self.notifier.notify(report, whatsapp=True)
        return report

    def debug_error(self, error_message: str, code: str = "", file_path: str = "") -> str:
        result = self.debugger.debug(error_message, code=code, file_path=file_path)
        self.notifier.notify(f"Debug Result:\n{result}", whatsapp=True)
        return result

    def scan_website(self, url: str) -> str:
        if not self.permissions.can_perform(Action.SCAN_WEBSITE):
            return self.permissions.request_approval(Action.SCAN_WEBSITE, f"Scan website: {url}")
        result = self.website_scanner.scan(url)
        report = self.website_scanner.format_report(result)
        self.notifier.notify(report, whatsapp=True)
        return report

    def fix_file(self, file_path: str, issue: str) -> str:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="ignore")
        return self.code_writer.apply_fix(str(path), content, issue)
