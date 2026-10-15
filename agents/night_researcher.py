"""
Night Researcher — Safe autonomous improvement mode.

While you sleep it:
- Expands knowledge from public sources
- Scans your code for secrets / simple issues
- Generates improvement proposals
- NEVER spends money, NEVER rents servers, NEVER auto-pushes
- Everything ends as a proposal waiting for your approval
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.ollama_client import OllamaClient
from core.permission_manager import PermissionManager, Action
from agents.knowledge_expander import KnowledgeExpander
from tools.secret_scanner import SecretScanner

logger = logging.getLogger("sentinel.night_researcher")


class NightResearcher:
    def __init__(
        self,
        ollama: Optional[OllamaClient] = None,
        expander: Optional[KnowledgeExpander] = None,
        permissions: Optional[PermissionManager] = None,
        project_root: str = ".",
    ):
        self.ollama = ollama or OllamaClient()
        self.expander = expander
        self.permissions = permissions or PermissionManager()
        self.project_root = Path(project_root)
        self.secret_scanner = SecretScanner()
        self.report_dir = Path("./memory/night_reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def run_cycle(self) -> Dict[str, Any]:
        """One full night research cycle. Safe by design."""
        results: Dict[str, Any] = {
            "started_at": datetime.utcnow().isoformat(),
            "knowledge": None,
            "secrets": None,
            "checks": None,
            "proposals": [],
            "summary": "",
        }

        # 1) Expand knowledge a little
        if self.expander:
            try:
                kr = self.expander.expand_once()
                results["knowledge"] = kr
                logger.info(f"Night knowledge expand: +{kr.get('pages_ingested', 0)}")
            except Exception as e:
                logger.error(f"Knowledge expand failed: {e}")
                results["knowledge"] = {"error": str(e)}

        # 2) Secret scan on project
        try:
            findings = self.secret_scanner.scan_directory(self.project_root, max_files=150)
            results["secrets"] = {
                "count": len(findings),
                "report": self.secret_scanner.format_report(findings),
            }
        except Exception as e:
            results["secrets"] = {"error": str(e)}

        # 3) Run bounded local syntax/tests; no shell and no network commands.
        try:
            results["checks"] = self._run_local_checks()
        except Exception as e:
            logger.error("Local code checks failed (%s)", type(e).__name__)
            results["checks"] = {"status": "error", "error": type(e).__name__}

        # 4) Generate improvement proposals (text only — no execution)
        try:
            proposals = self._generate_proposals(results)
            results["proposals"] = proposals
        except Exception as e:
            logger.error(f"Proposal generation failed: {e}")

        # 5) Write human-readable report
        summary = self._write_report(results)
        results["summary"] = summary
        results["finished_at"] = datetime.utcnow().isoformat()

        return results

    def _run_local_checks(self) -> Dict[str, Any]:
        """Run local syntax and unit tests with timeouts; never invokes a shell."""
        if os.getenv("SEKA_NIGHT_RUN_TESTS", "true").strip().lower() not in {"1", "true", "yes", "on"}:
            return {"status": "disabled", "reason": "SEKA_NIGHT_RUN_TESTS=false"}

        commands = [
            ("python_compile", [sys.executable, "-m", "compileall", "-q", "agents", "core", "scripts", "tools", "web"]),
            ("unit_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        ]
        results: Dict[str, Any] = {}
        timeout = max(30, min(int(os.getenv("SEKA_NIGHT_CHECK_TIMEOUT_SECONDS", "180")), 600))
        for name, command in commands:
            try:
                completed = subprocess.run(
                    command,
                    cwd=str(self.project_root),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                results[name] = {
                    "status": "passed" if completed.returncode == 0 else "failed",
                    "return_code": completed.returncode,
                    "output": (completed.stdout + "\n" + completed.stderr)[-4000:],
                }
            except subprocess.TimeoutExpired:
                results[name] = {"status": "timeout", "output": f"{timeout} saniyede tamamlanmadı."}
            except OSError as exc:
                results[name] = {"status": "unavailable", "output": type(exc).__name__}
        results["status"] = "passed" if all(
            isinstance(results.get(name), dict) and results[name].get("status") == "passed"
            for name, _ in commands
        ) else "attention_required"
        return results

    def _generate_proposals(self, context: Dict) -> List[str]:
        """Ask LLM for safe improvement ideas. Never executes them."""
        secrets_info = ""
        if context.get("secrets") and context["secrets"].get("count", 0) > 0:
            secrets_info = f"Gizli anahtar uyarısı: {context['secrets']['count']} bulgu var."

        knowledge_info = ""
        if context.get("knowledge") and not context["knowledge"].get("error"):
            knowledge_info = f"Yeni öğrenilen konu: {context['knowledge'].get('topic')}"

        prompt = f"""Sen bir kişisel AI ajanın gece araştırma modundasın.
Sadece ÖNERİ üret. Hiçbir komut çalıştırma, dosya silme, para harcama, sunucu kiralama yok.

Bağlam:
{secrets_info}
{knowledge_info}
{checks_info}

3-5 kısa, uygulanabilir iyileştirme önerisi yaz:
- Güvenlik
- Kod kalitesi
- Performans
- Dokümantasyon

Her öneri tek satır, eylem odaklı olsun.
Öneriler:"""

        try:
            reply = self.ollama.chat(
                prompt,
                system="Sadece güvenli, savunmacı ve uygulanabilir öneriler üret. Asla yıkıcı veya otonom finans önerisi verme.",
            )
            lines = [ln.strip(" -•\t") for ln in reply.splitlines() if ln.strip()]
            return lines[:6]
        except Exception as e:
            return [f"Öneri üretilemedi: {e}"]

    def _write_report(self, results: Dict) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
        path = self.report_dir / f"night_{ts}.md"

        lines = [
            f"# Night Research Report — {results.get('started_at')}",
            "",
            "## Bilgi Evreni",
        ]
        kn = results.get("knowledge") or {}
        if kn.get("error"):
            lines.append(f"Hata: {kn['error']}")
        else:
            lines.append(f"- Konu: {kn.get('topic')}")
            lines.append(f"- Yeni sayfa: {kn.get('pages_ingested', 0)}")
            lines.append(f"- Toplam bilgi: {kn.get('total_knowledge_pages', 0)}")

        lines.append("\n## Yerel Kod ve Test Kontrolü")
        checks = results.get("checks") or {}
        lines.append(f"- Genel durum: {checks.get('status', 'yapılmadı')}")
        for name in ("python_compile", "unit_tests"):
            item = checks.get(name) or {}
            if item:
                lines.append(f"- {name}: {item.get('status', 'bilinmiyor')} (çıkış: {item.get('return_code', '—')})")
                detail = str(item.get("output", ""))[-1200:]
                if detail:
                    lines.append("~~~text\n" + detail + "\n~~~")

        lines.append("\n## Gizli Anahtar Taraması")
        sec = results.get("secrets") or {}
        if sec.get("error"):
            lines.append(f"Hata: {sec['error']}")
        else:
            lines.append(sec.get("report", "Yok"))

        lines.append("\n## İyileştirme Önerileri (onayın gerekir)")
        for i, p in enumerate(results.get("proposals") or [], 1):
            lines.append(f"{i}. {p}")

        lines.append("\n---\nBu rapor sadece öneridir. Hiçbir değişiklik otomatik uygulanmadı.")

        text = "\n".join(lines)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=str(self.report_dir),
                prefix=".night-report-", suffix=".tmp", delete=False,
            ) as temp:
                temp.write(text)
                temp.flush()
                os.fsync(temp.fileno())
                temp_name = temp.name
            try:
                os.chmod(temp_name, 0o600)
            except OSError:
                pass
            os.replace(temp_name, path)
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
        logger.info(f"Night report written: {path}")
        return text
