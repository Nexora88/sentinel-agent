"""MKAOS ASGI giriş noktası — ekstra rotalar ve saatlik evren büyümesi.

Çalıştırma:
  uvicorn web.asgi:app --host 0.0.0.0 --port 8000

Docker/compose varsayılanı web.app:app ise CMD'yi web.asgi:app yapın
veya bu modülü import eden süreç kullanın.
"""
from __future__ import annotations

import logging
import os

from web.app import app, get_pipeline, get_user, night_scheduler
from web.extra_routes import register_extra_routes
from core.universe_growth import UniverseGrowthScheduler

logger = logging.getLogger("seka.asgi")

register_extra_routes(app, get_user, get_pipeline)

universe_growth: UniverseGrowthScheduler | None = None


@app.on_event("startup")
async def _start_universe_growth() -> None:
    global universe_growth
    try:

        def _expand():
            return get_pipeline("owner").knowledge_expander.expand_once()

        universe_growth = UniverseGrowthScheduler(
            _expand,
            interval_seconds=int(os.getenv("SEKA_UNIVERSE_INTERVAL_SECONDS", "3600")),
            enabled=os.getenv("SEKA_UNIVERSE_HOURLY", "false").lower()
            in {"1", "true", "yes", "on"},
        )
        universe_growth.start()
        logger.info("Universe growth enabled=%s", universe_growth.enabled)
    except Exception:
        logger.exception("Universe growth start failed")
        universe_growth = None


@app.on_event("shutdown")
async def _stop_universe_growth() -> None:
    if universe_growth:
        universe_growth.stop()


__all__ = ["app", "night_scheduler", "universe_growth"]
