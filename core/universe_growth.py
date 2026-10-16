"""Bilgi evreni saatlik büyüme — kapalı varsayılan, izin + limit.

ALLOW_WEB_RESEARCH=true olmadan ağ taraması yapmaz.
Durum memory/universe/growth.json içinde tutulur.
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional


class UniverseGrowthScheduler:
    def __init__(
        self,
        expand_fn: Callable[[], dict],
        *,
        interval_seconds: int = 3600,
        state_path: str = "./memory/universe/growth.json",
        enabled: bool | None = None,
    ):
        self.expand_fn = expand_fn
        self.interval = max(300, min(int(interval_seconds), 86400))
        self.state_path = Path(state_path)
        if enabled is None:
            enabled = os.getenv("SEKA_UNIVERSE_HOURLY", "false").lower() in {"1", "true", "yes", "on"}
        self.enabled = bool(enabled)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if not self.state_path.exists():
            return {"runs": 0, "last_run": None, "last_result": None}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {"runs": 0, "last_run": None, "corrupt": True}

    def _save(self, data: dict) -> None:
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, self.state_path)

    def status(self) -> dict[str, Any]:
        st = self._load()
        return {
            "enabled": self.enabled,
            "interval_seconds": self.interval,
            "web_research_allowed": os.getenv("ALLOW_WEB_RESEARCH", "false").lower() == "true",
            "runs": st.get("runs", 0),
            "last_run": st.get("last_run"),
            "last_result": st.get("last_result"),
            "note": "Saatlik büyüme SEKA_UNIVERSE_HOURLY=true ve ALLOW_WEB_RESEARCH=true ister.",
        }

    def run_once(self) -> dict:
        result = self.expand_fn()
        st = self._load()
        st["runs"] = int(st.get("runs") or 0) + 1
        st["last_run"] = datetime.now(timezone.utc).isoformat()
        st["last_result"] = {
            "pages_ingested": result.get("pages_ingested"),
            "deferred": result.get("deferred"),
            "topic": result.get("topic"),
            "reason": result.get("reason"),
        }
        self._save(st)
        return result

    def start(self) -> None:
        if not self.enabled or self._thread:
            return

        def loop() -> None:
            while not self._stop.is_set():
                try:
                    self.run_once()
                except Exception as exc:
                    st = self._load()
                    st["last_error"] = type(exc).__name__
                    st["last_run"] = datetime.now(timezone.utc).isoformat()
                    self._save(st)
                self._stop.wait(self.interval)

        self._thread = threading.Thread(target=loop, name="universe-growth", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
