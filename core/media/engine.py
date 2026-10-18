"""Bounded, persistent local-media job queue with an explicit resource gate."""
from __future__ import annotations
import json, os, shutil, threading, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

class MediaEngineError(RuntimeError): pass

class MediaEngine:
    def __init__(self, bridge, state_path: str = "./memory/media_jobs.json", min_free_ram_mb: int | None = None):
        self.bridge = bridge
        self.state_path = Path(state_path)
        self.min_free_ram_mb = max(512, min(int(min_free_ram_mb or os.getenv("MKAOS_MEDIA_MIN_FREE_RAM_MB", "2048")), 65536))
        self._lock = threading.RLock()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._recover_stale_jobs()

    def _recover_stale_jobs(self) -> None:
        if not self.state_path.exists():
            return
        jobs = self._read()
        changed = False
        for job in jobs:
            if job.get("status") == "running":
                job["status"] = "queued"
                job["reason"] = "Önceki süreç kesildi; güvenli yeniden deneme için kuyruğa alındı."
                changed = True
        if changed:
            self._write(jobs)

    def should_defer_heavy(self) -> bool:
        resources = self._resources()
        return resources["free_ram_mb"] is not None and resources["free_ram_mb"] < self.min_free_ram_mb

    def _read(self) -> list[dict]:
        if not self.state_path.exists(): return []
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            raise MediaEngineError("Medya kuyruğu okunamıyor; dosya korunuyor, otomatik sıfırlama yapılmadı.")

    def _write(self, jobs: list[dict]) -> None:
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(jobs[-200:], ensure_ascii=False, indent=2), encoding="utf-8")
        try: os.chmod(tmp, 0o600)
        except OSError: pass
        os.replace(tmp, self.state_path)

    @staticmethod
    def _resources() -> dict:
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {"free_ram_mb": int(mem.available / 1024 / 1024), "ram_known": True,
                    "cpu_count": os.cpu_count() or 1, "gpu_available": False}
        except Exception:
            return {"free_ram_mb": None, "ram_known": False, "cpu_count": os.cpu_count() or 1, "gpu_available": False}

    def submit(self, operation: str, payload: dict) -> dict:
        allowed = {
            "generate", "edit", "background", "video", "story_video", "understand_image",
            "analyze_video_frames", "text_to_video", "report_infographic",
            "poster", "code_card", "slideshow",
        }
        if operation not in allowed: raise MediaEngineError("Desteklenmeyen medya işlemi.")
        safe_payload = dict(payload)
        if any(isinstance(v, (bytes, bytearray)) for v in safe_payload.values()):
            raise MediaEngineError("Dosya baytları kuyruğa yazılmaz; yerel geçici dosya tanımlayıcısı gerekir.")
        if len(json.dumps(safe_payload, ensure_ascii=False)) > 8000:
            raise MediaEngineError("Medya görevi çok büyük.")
        job = {"id": uuid.uuid4().hex[:16], "operation": operation, "payload": safe_payload,
               "status": "queued", "created_at": datetime.now(timezone.utc).isoformat(),
               "reason": "İnsan/işletim paneli çalıştırmasını bekliyor.", "result": None}
        with self._lock:
            jobs = self._read(); jobs.append(job); self._write(jobs)
        return {k:v for k,v in job.items() if k != "payload"}

    def list_jobs(self, limit: int = 30) -> list[dict]:
        with self._lock:
            return [{k:v for k,v in job.items() if k != "payload"} for job in self._read()[-max(1,min(limit,100)):]][::-1]

    def run_job(self, job_id: str) -> dict:
        resources = self._resources()
        with self._lock:
            jobs = self._read()
            job = next((j for j in jobs if j.get("id") == job_id), None)
            if not job: raise MediaEngineError("Medya görevi bulunamadı.")
            if job["status"] == "running": raise MediaEngineError("Görev zaten çalışıyor.")
            if job["status"] == "done": return {k:v for k,v in job.items() if k != "payload"}
            if resources["free_ram_mb"] is not None and resources["free_ram_mb"] < self.min_free_ram_mb:
                job["status"] = "queued"; job["reason"] = "Boş RAM eşiğin altında; kaynaklar uygun olana kadar beklemede."
                self._write(jobs)
                return {k:v for k,v in job.items() if k != "payload"}
            job["status"] = "running"; job["reason"] = "Kaynak kontrolü geçti."; self._write(jobs)
        try:
            result = self.bridge.execute(job["operation"], job["payload"])
            status, reason = "done", "Tamamlandı."
        except Exception as exc:
            result = {"error": str(exc)[:500]}
            status, reason = "blocked", "Yerel adaptör/işlem hazır değil; dış servise geçiş yapılmadı."
        with self._lock:
            jobs = self._read()
            current = next(j for j in jobs if j.get("id") == job_id)
            current.update(status=status, reason=reason, result=result, finished_at=datetime.now(timezone.utc).isoformat())
            self._write(jobs)
            return {k:v for k,v in current.items() if k != "payload"}

    def render_report_infographic(self, report_text: str) -> dict:
        try:
            from core.media.local_canvas import LocalCanvas
            return LocalCanvas(self.state_path.parent / "generated_images").poster(
                "MKAOS / NIGHT WATCH REPORT", str(report_text or "Denetim tamamlandı.")
            )
        except Exception as exc:
            return {"success": False, "error": "Yerel rapor infografiği oluşturulamadı: " + type(exc).__name__}

    def capabilities(self) -> dict:
        return {"resources": self._resources(), "minimum_free_ram_mb": self.min_free_ram_mb,
                "queue_depth": sum(1 for j in self._read() if j.get("status") == "queued"),
                "model_bridge": self.bridge.capabilities()}
