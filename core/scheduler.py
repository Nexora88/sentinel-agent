"""
Scheduler for nightly / periodic runs.
Hardened against hung jobs and uncaught exceptions.
"""

from __future__ import annotations

import logging
import threading
from functools import wraps
from typing import Callable, Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("sentinel.scheduler")

# Default max runtime for a single job (seconds)
DEFAULT_JOB_TIMEOUT = 900  # 15 minutes


def with_timeout(func: Callable, timeout: int = DEFAULT_JOB_TIMEOUT) -> Callable:
    """Run func in a thread; if it exceeds timeout, log and return (does not kill thread hard on all platforms)."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        result_box: Dict = {"error": None, "done": False}

        def target():
            try:
                func(*args, **kwargs)
            except Exception as e:
                result_box["error"] = e
                logger.exception(f"Scheduled job '{getattr(func, '__name__', '?')}' failed: {e}")
            finally:
                result_box["done"] = True

        t = threading.Thread(target=target, daemon=True, name=f"job-{getattr(func, '__name__', 'unknown')}")
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            logger.error(
                f"Job '{getattr(func, '__name__', '?')}' exceeded {timeout}s timeout — skipped this cycle"
            )
            return
        if result_box["error"]:
            # already logged
            return

    return wrapper


class SentinelScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(
            job_defaults={
                "coalesce": True,           # collapse missed runs into one
                "max_instances": 1,         # never overlap same job
                "misfire_grace_time": 120,  # seconds
            }
        )
        self._jobs: Dict[str, str] = {}

    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        cron_expr: str,
        timeout: int = DEFAULT_JOB_TIMEOUT,
    ):
        """
        cron_expr example: "0 3 * * *"  (minute hour day month day_of_week)
        Each job is wrapped with timeout + exception isolation.
        """
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expr}")

        minute, hour, day, month, day_of_week = parts
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        )

        safe_func = with_timeout(func, timeout=timeout)

        self.scheduler.add_job(
            safe_func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self._jobs[job_id] = cron_expr
        logger.info(f"Scheduled job '{job_id}' cron='{cron_expr}' timeout={timeout}s")

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def list_jobs(self):
        return dict(self._jobs)
