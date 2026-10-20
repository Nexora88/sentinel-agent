"""Privacy-first weather/traffic adapters with explicit location consent and freshness labels.

No provider is queried unless the caller supplies consent and a provider implementation.
Cached results are always labelled stale when they exceed the configured freshness window.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class DataEnvelope:
    kind: str
    provider: str
    observed_at_utc: str
    fetched_at_utc: str
    freshness: str
    data: dict[str, Any]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


class ConsentRequired(PermissionError):
    """Raised when location-based data is requested without explicit consent."""


class ProviderUnavailable(RuntimeError):
    """Raised when a provider cannot supply fresh data and no cache exists."""


class LocationDataAdapter:
    """Base adapter; provider-specific network access is injected by the caller."""

    kind = "generic"

    def __init__(self, provider_name: str, fetcher: Callable[[Location], dict[str, Any]],
                 *, max_age_seconds: int = 1800) -> None:
        if max_age_seconds < 0:
            raise ValueError("max_age_seconds must be non-negative")
        self.provider_name = provider_name
        self._fetcher = fetcher
        self.max_age_seconds = max_age_seconds
        self._cache: DataEnvelope | None = None

    def get(self, location: Location, *, location_consent: bool,
            now: datetime | None = None) -> DataEnvelope:
        if not location_consent:
            raise ConsentRequired("Explicit location permission is required.")
        if not (-90 <= location.latitude <= 90 and -180 <= location.longitude <= 180):
            raise ValueError("Invalid latitude/longitude")
        current = (now or _utcnow()).astimezone(timezone.utc)
        try:
            payload = self._fetcher(location)
            if not isinstance(payload, dict):
                raise TypeError("Provider must return a dictionary")
            stamp = current.isoformat()
            observed = payload.get("observed_at_utc")
            if not isinstance(observed, str):
                current_payload = payload.get("current")
                observed = current_payload.get("time") if isinstance(current_payload, dict) else None
            if isinstance(observed, str):
                try:
                    observed = _parse_timestamp(observed + ("Z" if "T" in observed and "+" not in observed and not observed.endswith("Z") else "")).isoformat()
                except (TypeError, ValueError):
                    observed = stamp
            else:
                observed = stamp
            envelope = DataEnvelope(
                kind=self.kind, provider=self.provider_name, observed_at_utc=observed,
                fetched_at_utc=stamp, freshness="live", data=payload,
            )
            self._cache = envelope
            return envelope
        except Exception as exc:
            if self._cache is None:
                raise ProviderUnavailable("No fresh data or cached data is available.") from exc
            age = (current - _parse_timestamp(self._cache.fetched_at_utc)).total_seconds()
            return DataEnvelope(
                kind=self._cache.kind, provider=self._cache.provider,
                observed_at_utc=self._cache.observed_at_utc,
                fetched_at_utc=self._cache.fetched_at_utc,
                freshness="stale" if age > self.max_age_seconds else "cached",
                data=dict(self._cache.data),
            )


class WeatherAdapter(LocationDataAdapter):
    kind = "weather"


class TrafficAdapter(LocationDataAdapter):
    kind = "traffic"


def open_meteo_weather_adapter(*, timeout_seconds: float = 5.0) -> WeatherAdapter:
    """Create a live Open-Meteo adapter (no API key required for ordinary non-commercial use).

    The caller must still obtain location consent. Provider terms and usage limits apply.
    """
    import json
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    if not 0.2 <= timeout_seconds <= 20:
        raise ValueError("timeout_seconds must be between 0.2 and 20")

    def fetch(location: Location) -> dict[str, Any]:
        query = urlencode({
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,showers,snowfall,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m",
            "timezone": "UTC",
        })
        request = Request(
            "https://api.open-meteo.com/v1/forecast?" + query,
            headers={"Accept": "application/json", "User-Agent": "MKAOS/1.0 location-adapter"},
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            if response.status != 200:
                raise ProviderUnavailable("Weather provider returned a non-success status.")
            payload = json.loads(response.read(1_000_001).decode("utf-8"))
        current = payload.get("current")
        if not isinstance(current, dict) or len(current) > 32:
            raise ProviderUnavailable("Weather provider response schema was invalid.")
        return {
            "timezone": payload.get("timezone", "UTC"),
            "observed_at_utc": current.get("time"),
            "current": current,
            "units": payload.get("current_units", {}),
        }

    return WeatherAdapter("open-meteo", fetch)


def tomtom_traffic_adapter(*, api_key: str | None = None,
                           timeout_seconds: float = 5.0) -> TrafficAdapter:
    """Create a live TomTom flow adapter. API key is read at call time and never returned."""
    import json
    import os
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    if not 0.2 <= timeout_seconds <= 20:
        raise ValueError("timeout_seconds must be between 0.2 and 20")

    def fetch(location: Location) -> dict[str, Any]:
        secret = (api_key or os.getenv("TOMTOM_API_KEY", "")).strip()
        if not secret or len(secret) > 512:
            raise ProviderUnavailable("Traffic provider is not configured.")
        query = urlencode({
            "point": f"{location.latitude},{location.longitude}",
            "unit": "KMPH",
            "key": secret,
        })
        request = Request(
            "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?" + query,
            headers={"Accept": "application/json", "User-Agent": "MKAOS/1.0 location-adapter"},
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                if response.status != 200:
                    raise ProviderUnavailable("Traffic provider returned a non-success status.")
                payload = json.loads(response.read(1_000_001).decode("utf-8"))
        except Exception as exc:
            # Do not propagate URLs or provider exception messages: the URL contains the API key.
            raise ProviderUnavailable("Traffic provider request failed.") from exc
        flow = payload.get("flowSegmentData")
        if not isinstance(flow, dict):
            raise ProviderUnavailable("Traffic provider response schema was invalid.")
        allowed = ("frc", "currentSpeed", "freeFlowSpeed", "currentTravelTime",
                   "freeFlowTravelTime", "confidence", "roadClosure")
        return {key: flow[key] for key in allowed if key in flow}

    return TrafficAdapter("tomtom", fetch)
