"""
SEKA Job Bus — arka plan işlerinin canlı durumu.
UI SSE ile dinler. Kalıcı değil (process belleği).
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Callable, Deque, Dict, List, Optional


@dataclass
class Job:
    id: str
    kind: str
    title: str
    status: str = "queued"  # queued | running | done | error
    progress: float = 0.0
    message: str = ""
    result: Any = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> dict:
        d = asdict(self)
        # result may be large — keep short for list views
        if isinstance(d.get("result"), str) and len(d["result"]) > 2000:
            d["result"] = d["result"][:2000] + "…"
        return d


class JobBus:
    def __init__(self, max_jobs: int = 80):
        self._lock = threading.Lock()
        self._jobs: Dict[str, Job] = {}
        self._order: Deque[str] = deque(maxlen=max_jobs)
        self._listeners: List[Callable[[dict], None]] = []

    def subscribe(self, fn: Callable[[dict], None]) -> None:
        with self._lock:
            self._listeners.append(fn)

    def _emit(self, job: Job) -> None:
        payload = job.to_dict()
        for fn in list(self._listeners):
            try:
                fn(payload)
            except Exception:
                pass

    def create(self, kind: str, title: str) -> Job:
        jid = uuid.uuid4().hex[:12]
        job = Job(id=jid, kind=kind, title=title)
        with self._lock:
            self._jobs[jid] = job
            self._order.append(jid)
        self._emit(job)
        return job

    def update(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        result: Any = None,
        error: Optional[str] = None,
    ) -> Optional[Job]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = max(0.0, min(1.0, progress))
            if message is not None:
                job.message = message
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            job.updated_at = datetime.utcnow().isoformat() + "Z"
        self._emit(job)
        return job

    def get(self, job_id: str) -> Optional[dict]:
        with self._lock:
            j = self._jobs.get(job_id)
            return j.to_dict() if j else None

    def list_recent(self, limit: int = 20) -> List[dict]:
        with self._lock:
            ids = list(self._order)[-limit:]
            return [self._jobs[i].to_dict() for i in reversed(ids) if i in self._jobs]

    def run_in_thread(
        self,
        kind: str,
        title: str,
        fn: Callable[[Callable[..., None]], Any],
    ) -> str:
        """fn receives an update(status=..., progress=..., message=...) callback."""
        job = self.create(kind, title)

        def worker():
            def upd(**kwargs):
                self.update(job.id, **kwargs)

            self.update(job.id, status="running", progress=0.05, message="Başladı")
            try:
                result = fn(upd)
                self.update(
                    job.id,
                    status="done",
                    progress=1.0,
                    message="Tamam",
                    result=result,
                )
            except Exception as e:
                self.update(job.id, status="error", message=str(e), error=str(e))

        t = threading.Thread(target=worker, daemon=True, name=f"seka-job-{job.id}")
        t.start()
        return job.id


# Global singleton for web process
job_bus = JobBus()
