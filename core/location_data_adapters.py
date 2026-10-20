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
            envelope = DataEnvelope(
                kind=self.kind, provider=self.provider_name, observed_at_utc=stamp,
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
