"""Persistent, local-only nightly maintenance scheduler for SEKA.

The scheduled cycle creates an audit report and improvement proposals. It never
edits files, pushes commits, or contacts external services on its own.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler


class NightScheduler:
    def __init__(
        self,
        runner: Callable[[], dict],
        *,
        enabled: bool = False,
        hour: int = 3,
        minute: int = 0,
        timezone_name: str = "Europe/Istanbul",
        state_path: str = "./memory/night_scheduler.json",
    ) -> None:
        if not 0 <= int(hour) <= 23 or not 0 <= int(minute) <= 59:
            raise ValueError("Gece zamanlaması geçersiz; saat 0-23, dakika 0-59 olmalı.")
        self.runner = runner
        self.enabled = bool(enabled)
        self.hour = int(hour)
        self.minute = int(minute)
        self.timezone_name = timezone_name
        self.timezone = ZoneInfo(timezone_name)
        self.state_path = Path(state_path)
        self._run_lock = threading.Lock()
        self._scheduler: BackgroundScheduler | None = None

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def _read_state(self) -> dict:
        if not self.state_path.exists():
            return {}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {"status": "state_invalid"}
        except (OSError, ValueError):
            # Do not delete a damaged state file or pretend the last run succeeded.
            return {"status": "state_unreadable"}

    def _write_state(self, state: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        name = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=str(self.state_path.parent),
                prefix=".night-state-", suffix=".tmp", delete=False,
            ) as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
                name = handle.name
            try:
                os.chmod(name, 0o600)
            except OSError:
                pass
            os.replace(name, self.state_path)
            try:
                os.chmod(self.state_path, 0o600)
            except OSError:
                pass
        finally:
            if name and os.path.exists(name):
                os.unlink(name)

    def run_cycle(self) -> dict:
        """Run one bounded audit cycle; refuse overlapping executions."""
        if not self._run_lock.acquire(blocking=False):
            raise RuntimeError("Gece denetimi zaten çalışıyor; ikinci döngü başlatılmadı.")
        started = self._now()
        try:
            self._write_state({
                "status": "running",
                "started_at": started,
                "finished_at": None,
                "summary": "Yerel denetim sürüyor.",
                "error": None,
            })
            result = self.runner() or {}
            summary = str(result.get("summary") or "Denetim tamamlandı.")[:800]
            state = {
                "status": "success",
                "started_at": started,
                "finished_at": self._now(),
                "summary": summary,
                "error": None,
            }
            self._write_state(state)
            return {"status": "success", "summary": summary, "finished_at": state["finished_at"]}
        except Exception as exc:
            self._write_state({
                "status": "error",
                "started_at": started,
                "finished_at": self._now(),
                "summary": "Denetim tamamlanamadı; hata kaydedildi.",
                "error": type(exc).__name__,
            })
            raise
        finally:
            self._run_lock.release()

    def _dispatch(self) -> None:
        # Use the existing job queue so the panel can report progress and errors.
        from core.job_bus import job_bus

        job_bus.run_in_thread(
            "night_auto",
            "Otomatik gece denetimi",
            lambda update: self.run_cycle(),
        )

    def start(self) -> bool:
        if not self.enabled:
            return False
        if self._scheduler and self._scheduler.running:
            return True
        self._scheduler = BackgroundScheduler(timezone=self.timezone)
        self._scheduler.add_job(
            self._dispatch,
            "cron",
            hour=self.hour,
            minute=self.minute,
            id="seka-nightly-audit",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,
        )
        self._scheduler.start()
        return True

    def stop(self) -> None:
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def status(self) -> dict:
        next_run = None
        if self._scheduler and self._scheduler.running:
            job = self._scheduler.get_job("seka-nightly-audit")
            if job and job.next_run_time:
                next_run = job.next_run_time.isoformat()
        return {
            "enabled": self.enabled,
            "running": bool(self._scheduler and self._scheduler.running),
            "timezone": self.timezone_name,
            "scheduled_time": f"{self.hour:02d}:{self.minute:02d}",
            "next_run_at": next_run,
            "last_run": self._read_state(),
            "execution_policy": "rapor ve öneri; otomatik dosya yazma veya push yok",
        }
