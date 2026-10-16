"""
İzin kontrollü kod yazma / düzeltme.
Yalnızca proje kökü altındaki güvenli yollara yazar.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from core.permission_manager import PermissionManager, Action

logger = logging.getLogger("sentinel.code_writer")

ALLOWED_ROOTS = (
    "agents",
    "core",
    "tools",
    "web",
    "tests",
    "docs",
    "config",
    "scripts",
    "engine",
    "benchmarks",
)

SYSTEM_TR = (
    "Sen dikkatli bir kıdemli yazılımcısın. Yalnızca gerekli değişiklikleri yap. "
    "Yanıt olarak SADECE düzeltilmiş dosyanın tam içeriğini ver; açıklama ekleme."
)


class CodeWriter:
    """Kod üretir veya düzeltir; diske yazmadan önce izin ister."""

    def __init__(
        self,
        ollama=None,
        permissions: Optional[PermissionManager] = None,
        project_root: Optional[Path] = None,
    ):
        self.ollama = ollama
        self.permissions = permissions or PermissionManager()
        self.project_root = (project_root or Path(".")).resolve()

    def _client(self):
        if self.ollama is not None:
            return self.ollama
        from core.ollama_client import OllamaClient

        self.ollama = OllamaClient()
        return self.ollama

    def _safe_path(self, file_path: str) -> Path:
        path = Path(file_path)
        if path.is_absolute():
            resolved = path.resolve()
        else:
            resolved = (self.project_root / path).resolve()
        try:
            relative = resolved.relative_to(self.project_root)
        except ValueError as exc:
            raise PermissionError("Dosya yolu proje kökünün dışında.") from exc
        if not relative.parts or relative.parts[0] not in ALLOWED_ROOTS:
            raise PermissionError(
                f"Yalnızca şu kökler altında yazılabilir: {', '.join(ALLOWED_ROOTS)}"
            )
        if any(part.startswith(".") for part in relative.parts):
            raise PermissionError("Gizli dizinlere yazma engellendi.")
        name = relative.name.lower()
        if name in {".env", ".env.local", "credentials.json", "id_rsa", "id_ed25519"}:
            raise PermissionError("Sır dosyalarına yazma engellendi.")
        return resolved

    def propose_fix(self, file_path: str, content: str, issue_description: str) -> str:
        prompt = f"""Aşağıdaki sorunu düzelt. Gerekli olmayan yerleri değiştirme.
Yalnızca düzeltilmiş dosyanın tamamını döndür.

Sorun:
{issue_description}

Dosya ({file_path}):
```
{content[:120000]}
```
"""
        client = self._client()
        fixed = client.chat(prompt, system=SYSTEM_TR)
        text = (fixed or "").strip()
        if text.startswith("```"):
            lines = text.splitlines()
            # strip markdown fence
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return text

    def propose_new(self, file_path: str, specification: str) -> str:
        prompt = f"""Şu dosya için sıfırdan kod yaz. Yalnızca dosya içeriğini döndür.

Hedef yol: {file_path}

İstek:
{specification}
"""
        client = self._client()
        out = client.chat(prompt, system=SYSTEM_TR)
        text = (out or "").strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return text

    def write_file(self, file_path: str, new_content: str, reason: str) -> str:
        try:
            path = self._safe_path(file_path)
        except PermissionError as exc:
            return f"❌ {exc}"

        if not self.permissions.can_perform(Action.MODIFY_FILES):
            return self.permissions.request_approval(
                Action.MODIFY_FILES,
                f"Dosya yaz/düzelt: {file_path}\nGerekçe: {reason}",
                context={"file": str(path), "preview": new_content[:500]},
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_content, encoding="utf-8")
        logger.info("File written: %s", path)
        return f"✅ Dosya yazıldı: {path}"

    def apply_fix(self, file_path: str, content: str, issue: str) -> str:
        fixed = self.propose_fix(file_path, content, issue)
        return self.write_file(file_path, fixed, reason=issue)
