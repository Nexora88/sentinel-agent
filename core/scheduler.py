"""
Scheduler for nightly runs.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from core.config import settings

logger = logging.getLogger("sentinel.scheduler")


class SentinelScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._jobs = {}

    def add_cron_job(self, job_id: str, func: Callable, cron_expr: str):
        """
        cron_expr example: "0 3 * * *"  (minute hour day month day_of_week)
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

        self.scheduler.add_job(func, trigger=trigger, id=job_id, replace_existing=True)
        self._jobs[job_id] = cron_expr
        logger.info(f"Scheduled job '{job_id}' with cron '{cron_expr}'")

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    def list_jobs(self):
        return self._jobs
