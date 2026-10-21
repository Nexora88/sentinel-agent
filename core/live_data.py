"""Opt-in live weather and traffic adapters with honest source timestamps.

No mock values or hidden provider fallback are returned. Network calls are denied unless
the operator explicitly selects networked mode and enables the specific integration.
"""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from typing import Any

import requests

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
TRAFFIC_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
CACHE_TTL_SECONDS = 300
MAX_CACHE_ENTRIES = 512
_lock = threading.Lock()
_cache: dict[tuple[str, float, float], tuple[float, dict[str, Any]]] = {}


class LiveDataError(RuntimeError):
    """A provider is disabled, unavailable, or returned an invalid response."""


def _enabled(feature: str) -> None:
    mode = os.getenv("MKAOS_NETWORK_MODE", "offline").strip().lower()
    if mode not in {"networked", "online"}:
        raise LiveDataError("Ağ modu kapalı; canlı sağlayıcı isteği engellendi.")
    if os.getenv(f"ALLOW_LIVE_{feature.upper()}", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        raise LiveDataError(f"Canlı {feature} entegrasyonu açıkça etkinleştirilmemiş.")


def _coordinates(latitude: float, longitude: float) -> tuple[float, float]:
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError):
        raise LiveDataError("Enlem ve boylam sayısal olmalıdır.") from None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise LiveDataError("Enlem veya boylam geçerli aralıkta değil.")
    return round(lat, 4), round(lon, 4)


def _cached(provider: str, lat: float, lon: float) -> dict[str, Any] | None:
    with _lock:
        entry = _cache.get((provider, lat, lon))
        if entry and time.monotonic() - entry[0] < CACHE_TTL_SECONDS:
            return {**entry[1], "cache": "hit"}
        if entry:
            _cache.pop((provider, lat, lon), None)
    return None


def _store(provider: str, lat: float, lon: float, payload: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        key = (provider, lat, lon)
        _cache.pop(key, None)
        while len(_cache) >= MAX_CACHE_ENTRIES:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (time.monotonic(), payload)
    return {**payload, "cache": "miss"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_weather(latitude: float, longitude: float) -> dict[str, Any]:
    _enabled("weather")
    lat, lon = _coordinates(latitude, longitude)
    cached = _cached("open-meteo", lat, lon)
    if cached:
        return cached
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
        "timezone": "UTC",
    }
    try:
        response = requests.get(WEATHER_URL, params=params, timeout=(3, 8))
        response.raise_for_status()
        data = response.json()
        current = data.get("current")
        if not isinstance(current, dict) or not current.get("time"):
            raise ValueError("missing current observations")
        payload = {
            "provider": "Open-Meteo",
            "source": WEATHER_URL,
            "fetched_at": _now(),
            "observed_at": current["time"],
            "coordinates": {"latitude": lat, "longitude": lon},
            "timezone": data.get("timezone", "UTC"),
            "units": data.get("current_units", {}),
            "current": current,
            "cache_ttl_seconds": CACHE_TTL_SECONDS,
        }
        return _store("open-meteo", lat, lon, payload)
    except Exception:
        raise LiveDataError("Hava durumu sağlayıcısı yanıt vermedi veya geçerli veri döndürmedi.") from None


def get_traffic(latitude: float, longitude: float) -> dict[str, Any]:
    _enabled("traffic")
    lat, lon = _coordinates(latitude, longitude)
    api_key = os.getenv("TOMTOM_API_KEY", "").strip()
    if not api_key:
        raise LiveDataError("Canlı trafik için TOMTOM_API_KEY yapılandırılmalıdır.")
    cached = _cached("tomtom-traffic", lat, lon)
    if cached:
        return cached
    try:
        response = requests.get(
            TRAFFIC_URL,
            params={"point": f"{lat},{lon}", "unit": "KMPH", "key": api_key},
            timeout=(3, 8),
        )
        response.raise_for_status()
        data = response.json()
        flow = data.get("flowSegmentData")
        if not isinstance(flow, dict) or "currentSpeed" not in flow:
            raise ValueError("missing traffic flow")
        payload = {
            "provider": "TomTom Traffic Flow",
            "source": TRAFFIC_URL,
            "fetched_at": _now(),
            "observed_at": data.get("dateTime", data.get("flowSegmentData", {}).get("dateTime")),
            "coordinates": {"latitude": lat, "longitude": lon},
            "units": {"speed": "km/h"},
            "current": {
                "current_speed": flow.get("currentSpeed"),
                "free_flow_speed": flow.get("freeFlowSpeed"),
                "confidence": flow.get("confidence"),
                "road_closure": flow.get("roadClosure"),
                "frc": flow.get("frc"),
                "description": flow.get("description"),
            },
            "cache_ttl_seconds": CACHE_TTL_SECONDS,
        }
        return _store("tomtom-traffic", lat, lon, payload)
    except Exception:
        raise LiveDataError("Trafik sağlayıcısı yanıt vermedi veya geçerli veri döndürmedi.") from None
