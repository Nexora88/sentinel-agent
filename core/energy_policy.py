"""
Energy-aware scheduling policy (local heuristics only).
Does not read smart meters or control hardware — only time-of-day / simple load hints.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict


def is_off_peak(now: datetime | None = None) -> bool:
    """Default: treat 00:00–07:00 local as off-peak (cheaper / cooler in many regions)."""
    now = now or datetime.now()
    start = int(os.getenv("OFF_PEAK_START_HOUR", "0"))
    end = int(os.getenv("OFF_PEAK_END_HOUR", "7"))
    h = now.hour
    if start < end:
        return start <= h < end
    # wraps midnight
    return h >= start or h < end


def should_run_heavy_job(job_name: str = "") -> Dict[str, Any]:
    """
    Advise whether a heavy RAG / research job should run now.
    FORCE_HEAVY_JOBS=true overrides.
    """
    if os.getenv("FORCE_HEAVY_JOBS", "").lower() in ("1", "true", "yes"):
        return {"allow": True, "reason": "FORCE_HEAVY_JOBS enabled"}

    off = is_off_peak()
    if off:
        return {"allow": True, "reason": "off-peak window", "off_peak": True}

    # Light jobs always ok; heavy ones deferred preference
    heavy = job_name in {"universe_expand", "night_research", "curiosity", "paper_finance"}
    if heavy:
        return {
            "allow": True,  # still allow — policy is advisory unless STRICT_ENERGY=true
            "prefer_defer": os.getenv("STRICT_ENERGY", "").lower() in ("1", "true", "yes"),
            "reason": "peak hours — prefer defer if STRICT_ENERGY",
            "off_peak": False,
        }
    return {"allow": True, "reason": "light job", "off_peak": False}


def policy_status() -> Dict[str, Any]:
    return {
        "off_peak_now": is_off_peak(),
        "off_peak_window": f"{os.getenv('OFF_PEAK_START_HOUR', '0')}-{os.getenv('OFF_PEAK_END_HOUR', '7')}",
        "strict_energy": os.getenv("STRICT_ENERGY", "false"),
        "force_heavy": os.getenv("FORCE_HEAVY_JOBS", "false"),
    }
