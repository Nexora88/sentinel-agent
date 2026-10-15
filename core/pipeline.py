"""
SEKA Pipeline — yerel süper ajan orkestrasyonu.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from core.ollama_client import OllamaClient
from core.rag import MemoryStore
from core.personal_memory import PersonalMemory
from core.permission_manager import PermissionManager, Action
from core.energy_policy import should_run_heavy_job, policy_status
from core.action_planner import ActionPlanner
from core.model_router import ModelRouter
from tools.git_tools import GitTools
from tools.notifier import Notifier
from tools.code_writer import CodeWriter
from tools.website_scanner import WebsiteScanner
from tools.github_client import GitHubClient
from tools.finance_engine import FinanceEngine
from tools.autonomous_finance import AutonomousFinance
from tools.image_gen import ImageGenerator
from tools.secret_scanner import SecretScanner
from tools.document_ingester import DocumentIngester
from tools.license_checker import LicenseChecker
from tools.local_discovery import LocalDiscovery
from tools.document_assistant import DocumentAssistant
from tools.legacy_backup import LegacyBackup
from tools.knowledge_pack import KnowledgePack
from agents.code_reviewer import CodeReviewerAgent
from agents.security_scanner import SecurityScannerAgent
from agents.learner import LearnerAgent
from agents.reporter import ReporterAgent
from agents.debugger import DebuggerAgent
from agents.personal_assistant import PersonalAssistant
from agents.knowledge_expander import KnowledgeExpander
from agents.night_researcher import NightResearcher
from agents.curiosity import CuriosityEngine
from agents.podcast_draft import PodcastDraft

logger = logging.getLogger("seka.pipeline")


class SentinelPipeline:
    def __init__(self):
        self.router = ModelRouter()
        self.ollama = self.router.default
        self.memory = MemoryStore(ollama=self.ollama)
        self.personal_memory = PersonalMemory(ollama=self.ollama)
        self.permissions = PermissionManager()
        self.git = GitTools()
        self.notifier = Notifier()
        self.code_writer = CodeWriter(ollama=self.ollama, permissions=self.permissions)
        self.website_scanner = WebsiteScanner()

        self.github = GitHubClient(permissions=self.permissions)
        self.finance = FinanceEngine(ollama=self.ollama)
        self.auto_finance = AutonomousFinance(ollama=self.ollama)
        self.image_gen = ImageGenerator()
        self.secret_scanner = SecretScanner()
        self.doc_ingester = DocumentIngester(ollama=self.ollama, memory=self.memory)
        self.license_checker = LicenseChecker()
        self.local_discovery = LocalDiscovery()
        self.doc_assistant = DocumentAssistant(ollama=self.ollama)
        self.legacy = LegacyBackup()
        self.podcast = PodcastDraft(ollama=self.router.for_task("podcast"))
        self.packs = KnowledgePack()
        self.planner = ActionPlanner(ollama=self.router.for_task("plan"))

        self.reviewer = CodeReviewerAgent(ollama=self.ollama, memory=self.memory)
        self.security = SecurityScannerAgent(ollama=self.ollama, memory=self.memory)
        self.learner = LearnerAgent(ollama=self.ollama, memory=self.memory)
        self.reporter = ReporterAgent(ollama=self.ollama)
        self.debugger = DebuggerAgent(ollama=self.ollama, memory=self.memory)

        self.expander = KnowledgeExpander(ollama=self.ollama, memory=self.memory)
        self.night = NightResearcher(
            ollama=self.router.for_task("night"),
            expander=self.expander,
            permissions=self.permissions,
        )
        self.curiosity = CuriosityEngine(ollama=self.ollama, expander=self.expander)

        self.assistant = PersonalAssistant(
            ollama=self.router.for_task("chat"),
            memory=self.personal_memory,
            permissions=self.permissions,
            pipeline=self,
        )

    def chat(self, message: str) -> str:
        return self.assistant.chat(message)

    def status(self) -> str:
        base = self.assistant.get_status()
        uni = self.expander.get_status()
        fin = self.auto_finance.get_status()
        cur = self.curiosity.get_status()
        energy = policy_status()
        models = self.router.info()
        gh = "bağlı" if self.github.enabled else "token yok"
        return (
            f"{base}\n\n"
            f"◈ SEKA | modeller: hızlı={models['fast']} derin={models['deep']}\n"
            f"🌌 Bilgi: {uni.get('total_pages', 0)} · Merak: {cur.get('explored_count', 0)}\n"
            f"⚡ Enerji off-peak={energy.get('off_peak_now')}\n"
            f"🐙 GitHub: {gh}\n"
            f"💰 Paper: ${fin.get('equity', 0):.2f} ({fin.get('pnl_total_pct', 0):+.1f}%)"
        )

    def expand_knowledge(self, topic: Optional[str] = None) -> dict:
        advice = should_run_heavy_job("universe_expand")
        if advice.get("prefer_defer") and not advice.get("off_peak"):
            return {
                "topic": topic or "(deferred)",
                "pages_ingested": 0,
                "deferred": True,
                "reason": advice.get("reason"),
                "total_knowledge_pages": self.expander.get_status().get("total_pages", 0),
            }
        if topic:
            self.expander.add_seed_topic(topic)
        return self.expander.expand_once(extra_topics=[topic] if topic else None)

    def run_curiosity(self) -> dict:
        return self.curiosity.run_once()

    def run_night_research(self) -> dict:
        return self.night.run_cycle()

    def podcast_from_night(self) -> dict:
        return self.podcast.from_latest_night_report()

    def create_plan(self, goal: str) -> dict:
        return self.planner.create_plan(goal)

    def run_plan_safe(self, plan_id: str) -> dict:
        return self.planner.execute_safe_steps(plan_id, self)

    def export_knowledge_pack(self, title: str = "SEKA Araştırma Paketi") -> dict:
        return self.packs.export_pack(title=title)

    def run_finance_cycle(self, context: str = "") -> dict:
        if not context:
            try:
                context = self.expander.search_knowledge(
                    "cryptocurrency market news trends", k=4
                )
            except Exception:
                context = ""
        return self.auto_finance.run_cycle(context=context)

    def finance_status(self) -> dict:
        return self.auto_finance.get_status()

    def scan_secrets(self, path: str = ".") -> str:
        findings = self.secret_scanner.scan_directory(path)
        report = self.secret_scanner.format_report(findings)
        self.notifier.notify(report, whatsapp=True)
        return report

    def check_licenses(self, path: str = ".") -> str:
        result = self.license_checker.scan_tree(path)
        return self.license_checker.format_report(result)

    def discover_local(self) -> dict:
        return self.local_discovery.scan_localhost()

    def discover_local_report(self) -> str:
        return self.local_discovery.format_report(self.discover_local())

    def analyze_document_text(self, text: str) -> str:
        result = self.doc_assistant.analyze_text(text)
        return self.doc_assistant.format_report(result)

    def legacy_export(self, passphrase: str, out_path: str = "./memory/legacy_backup.bin") -> str:
        path = self.legacy.export(passphrase, out_path=out_path)
        return f"Legacy yedek yazıldı: {path}"

    def ingest_document(self, file_path: str) -> dict:
        return self.doc_ingester.ingest_file(file_path, analyze=True)

    def run_on_repo(self, repo_url: str, branch: str = "main", max_files: int = 8) -> str:
        logger.info(f"Pipeline on {repo_url}")
        repo_path = self.git.clone_or_update(repo_url, branch=branch)
        repo_name = repo_path.name
        changed = self.git.get_changed_files(repo_path)
        if not changed:
            changed = self.git.list_python_files(repo_path, limit=max_files)
        changed = changed[:max_files]
        code_reviews, security_findings = [], []
        for file_path in changed:
            content = self.git.get_file_content(repo_path, file_path)
            if not content or len(content) < 20:
                continue
            language = Path(file_path).suffix.lstrip(".") or "text"
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
            code_reviews=code_reviews, security_findings=security_findings, repo=repo_name
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
        self.notifier.notify(f"Debug:\n{result}", whatsapp=True)
        return result

    def scan_website(self, url: str) -> str:
        import os
        if os.getenv("ALLOW_SITE_SCANNING", "false").lower() != "true":
            return "Gizlilik koruması: site taraması varsayılan olarak kapalı. ALLOW_SITE_SCANNING=true ile yalnızca izinli hedeflerde aç."
        if not self.permissions.can_perform(Action.SCAN_WEBSITE):
            return self.permissions.request_approval(Action.SCAN_WEBSITE, f"Scan: {url}")
        result = self.website_scanner.scan(url)
        report = self.website_scanner.format_report(result)
        self.notifier.notify(report, whatsapp=True)
        return report

    def fix_file(self, file_path: str, issue: str) -> str:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="ignore")
        return self.code_writer.apply_fix(str(path), content, issue)
