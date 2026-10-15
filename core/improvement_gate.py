"""Human-reviewed code-improvement proposal storage; never applies or executes patches."""
from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


class ImprovementProposalError(ValueError):
    """A proposed code change violates the review-gate policy."""


ALLOWED_ROOTS = {"agents", "core", "tools", "web", "tests", "docs", "config"}
BLOCKED_NAMES = {".env", ".env.local", ".env.production", "secrets.py", "credentials.json", "id_rsa"}


def validate_candidate(title: str, rationale: str, files: list[str], patch: str, test_plan: list[str]) -> dict:
    title, rationale, patch = str(title or "").strip(), str(rationale or "").strip(), str(patch or "")
    if not title or len(title) > 160:
        raise ImprovementProposalError("Başlık 1-160 karakter olmalı.")
    if not rationale or len(rationale) > 4000:
        raise ImprovementProposalError("Gerekçe 1-4000 karakter olmalı.")
    if not isinstance(files, list) or not 1 <= len(files) <= 20:
        raise ImprovementProposalError("1-20 hedef dosya belirtilmeli.")
    normalized = []
    for name in files:
        path = str(name or "").replace("\\", "/").strip()
        parts = Path(path).parts
        if (not path or path.startswith("/") or ".." in parts or len(parts) < 2
                or parts[0] not in ALLOWED_ROOTS or Path(path).name.lower() in BLOCKED_NAMES
                or Path(path).name.lower().startswith(".env")):
            raise ImprovementProposalError("Hedef yol izin verilen kod/dokümantasyon alanında değil.")
        if path not in normalized:
            normalized.append(path)
    if not patch.strip() or len(patch.encode("utf-8")) > 50_000:
        raise ImprovementProposalError("Yama boş veya 50 KB sınırını aşıyor.")
    if not isinstance(test_plan, list) or not 1 <= len(test_plan) <= 20:
        raise ImprovementProposalError("1-20 doğrulama adımı belirtilmeli.")
    tests = [str(item or "").strip()[:500] for item in test_plan]
    if any(not item for item in tests):
        raise ImprovementProposalError("Doğrulama adımları boş olamaz.")
    return {"title": title, "rationale": rationale, "files": normalized,
            "patch": patch, "test_plan": tests}


class ImprovementProposalStore:
    """Tenant-local proposal ledger. Approval changes metadata only; no patch execution."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, proposal_id: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{16}", str(proposal_id or "")):
            raise ImprovementProposalError("Geçersiz öneri kimliği.")
        return self.root / (proposal_id + ".json")

    def create(self, **candidate) -> dict:
        clean = validate_candidate(**candidate)
        proposal_id = uuid.uuid4().hex[:16]
        record = {**clean, "id": proposal_id, "status": "pending_review",
                  "created_at": datetime.now(timezone.utc).isoformat(),
                  "execution": "never_auto_applied"}
        self._write(self._path(proposal_id), record)
        return {k: v for k, v in record.items() if k != "patch"}

    def list(self, limit: int = 50) -> list[dict]:
        items = []
        for path in sorted(self.root.glob("????????????????.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and re.fullmatch(r"[a-f0-9]{16}", str(data.get("id", ""))):
                    items.append({k: v for k, v in data.items() if k != "patch"})
            except (OSError, ValueError):
                continue
        return items[:max(1, min(int(limit), 100))]

    def approve_for_review(self, proposal_id: str, confirmation: str) -> dict:
        if confirmation != "READY_FOR_HUMAN_CODE_REVIEW":
            raise ImprovementProposalError("Açık insan onayı metni gerekli.")
        path = self._path(proposal_id)
        if not path.is_file():
            raise ImprovementProposalError("Öneri bulunamadı.")
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("status") != "pending_review":
            raise ImprovementProposalError("Öneri zaten incelenmiş veya onaylanmış.")
        data["status"] = "ready_for_human_review"
        data["review_requested_at"] = datetime.now(timezone.utc).isoformat()
        data["execution"] = "never_auto_applied"
        self._write(path, data)
        return {k: v for k, v in data.items() if k != "patch"}

    @staticmethod
    def _write(path: Path, data: dict) -> None:
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent),
                                             prefix=".proposal-", suffix=".tmp", delete=False) as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
                temp_name = handle.name
            try:
                os.chmod(temp_name, 0o600)
            except OSError:
                pass
            os.replace(temp_name, path)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
