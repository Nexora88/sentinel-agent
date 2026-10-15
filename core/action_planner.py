"""
Aksiyon Plan Motoru — tek emirden çok adımlı plan.
Yıkıcı adımlar ASLA otomatik çalışmaz; onay kuyruğuna düşer.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.ollama_client import OllamaClient
from core.safety import is_forbidden_shell

logger = logging.getLogger("seka.planner")

SAFE_STEP_TYPES = {
    "expand_knowledge",
    "curiosity",
    "night_research",
    "scan_website",
    "scan_secrets",
    "check_licenses",
    "finance_analyze",
    "paper_finance_cycle",
    "ingest_hint",
    "report_only",
    "podcast_draft",
    "discover_local",
}

# These require explicit human approval even to run
APPROVAL_REQUIRED = {
    "modify_files",
    "git_push",
    "git_commit",
    "create_pr",
}


class ActionPlanner:
    def __init__(self, ollama: Optional[OllamaClient] = None, store_dir: str = "./memory/plans"):
        self.ollama = ollama or OllamaClient()
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def _save(self, plan: dict) -> None:
        path = self.store_dir / f"{plan['id']}.json"
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_plans(self, limit: int = 15) -> List[dict]:
        files = sorted(self.store_dir.glob("*.json"), reverse=True)[:limit]
        out = []
        for f in files:
            try:
                out.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                pass
        return out

    def get(self, plan_id: str) -> Optional[dict]:
        path = self.store_dir / f"{plan_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def create_plan(self, goal: str) -> dict:
        goal = (goal or "").strip()
        if len(goal) < 5:
            return {"success": False, "error": "Hedef çok kısa"}

        prompt = f"""Kullanıcı hedefi için 3-6 adımlık JSON plan üret.

Kurallar:
- Sadece şu step type'lar: {sorted(SAFE_STEP_TYPES | APPROVAL_REQUIRED)}
- Shell/rm/curl|sh ASLA
- Para harcama, bulut kiralama, gerçek trading YOK
- Her adım: type, title, detail, needs_approval (bool)
- modify_files / git_* için needs_approval=true zorunlu

Hedef: {goal}

Sadece JSON dizi döndür:
[{{"type":"...","title":"...","detail":"...","needs_approval":false}}]
"""
        try:
            raw = self.ollama.chat(
                prompt,
                system="SEKA plan motoru. Sadece geçerli JSON dizi. Türkçe title/detail.",
            )
            steps = self._parse_steps(raw)
        except Exception as e:
            logger.error(f"plan failed: {e}")
            steps = self._fallback_steps(goal)

        # Sanitize
        clean = []
        for s in steps[:8]:
            stype = str(s.get("type", "report_only"))
            if stype not in SAFE_STEP_TYPES and stype not in APPROVAL_REQUIRED:
                stype = "report_only"
            detail = str(s.get("detail", ""))[:500]
            if is_forbidden_shell(detail):
                continue
            needs = bool(s.get("needs_approval")) or stype in APPROVAL_REQUIRED
            clean.append({
                "id": uuid.uuid4().hex[:8],
                "type": stype,
                "title": str(s.get("title", stype))[:120],
                "detail": detail,
                "needs_approval": needs,
                "status": "pending",
            })

        plan = {
            "id": uuid.uuid4().hex[:12],
            "goal": goal,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "status": "draft",
            "steps": clean,
            "success": True,
        }
        self._save(plan)
        return plan

    def _parse_steps(self, raw: str) -> List[dict]:
        m = re.search(r"\[.*\]", raw, re.S)
        if not m:
            return self._fallback_steps(raw[:200])
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return self._fallback_steps("")

    def _fallback_steps(self, goal: str) -> List[dict]:
        return [
            {"type": "expand_knowledge", "title": "Konuyu araştır", "detail": goal, "needs_approval": False},
            {"type": "scan_secrets", "title": "Gizli anahtar tara", "detail": ".", "needs_approval": False},
            {"type": "report_only", "title": "Özet rapor", "detail": goal, "needs_approval": False},
        ]

    def execute_safe_steps(self, plan_id: str, pipeline) -> dict:
        """Run only steps that do not need approval."""
        plan = self.get(plan_id)
        if not plan:
            return {"success": False, "error": "Plan yok"}

        results = []
        for step in plan.get("steps", []):
            if step.get("needs_approval") or step.get("status") == "done":
                continue
            stype = step["type"]
            try:
                out = self._run_step(stype, step, pipeline)
                step["status"] = "done"
                step["result"] = str(out)[:1500]
                results.append({"title": step["title"], "ok": True})
            except Exception as e:
                step["status"] = "error"
                step["result"] = str(e)
                results.append({"title": step["title"], "ok": False, "error": str(e)})

        plan["status"] = "partial" if any(s.get("needs_approval") for s in plan["steps"]) else "done"
        plan["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._save(plan)
        return {"success": True, "plan": plan, "ran": results}

    def _run_step(self, stype: str, step: dict, pipeline) -> str:
        detail = step.get("detail", "")
        if stype == "expand_knowledge":
            r = pipeline.expand_knowledge(topic=detail or None)
            return f"+{r.get('pages_ingested')} sayfa · {r.get('topic')}"
        if stype == "curiosity":
            r = pipeline.run_curiosity()
            return r.get("topic", "ok")
        if stype == "night_research":
            r = pipeline.run_night_research()
            return (r.get("summary") or "")[:400]
        if stype == "scan_website" and detail.startswith("http"):
            return pipeline.scan_website(detail)[:500]
        if stype == "scan_secrets":
            return pipeline.scan_secrets(detail or ".")[:500]
        if stype == "check_licenses":
            return pipeline.check_licenses(detail or ".")[:500]
        if stype == "finance_analyze":
            return pipeline.finance.analyze(detail or "piyasa özeti")[:500]
        if stype == "paper_finance_cycle":
            r = pipeline.run_finance_cycle()
            return str(r.get("decision"))
        if stype == "podcast_draft":
            r = pipeline.podcast_from_night()
            return r.get("path") or r.get("error", "")
        if stype == "discover_local":
            return pipeline.discover_local_report()
        if stype == "report_only":
            return f"Rapor notu: {detail}"
        if stype == "ingest_hint":
            return f"Belge paneline yükle: {detail}"
        return f"Atlandı: {stype}"
