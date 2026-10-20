import unittest
from datetime import datetime, timedelta, timezone

from core.location_data_adapters import (
    ConsentRequired, Location, ProviderUnavailable, TrafficAdapter, WeatherAdapter,
)


class LocationDataAdapterTests(unittest.TestCase):
    def setUp(self):
        self.location = Location(41.0082, 28.9784)
        self.now = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)

    def test_location_consent_is_required_before_provider_call(self):
        called = []
        adapter = WeatherAdapter("test", lambda loc: called.append(loc) or {"temp_c": 19})
        with self.assertRaises(ConsentRequired):
            adapter.get(self.location, location_consent=False, now=self.now)
        self.assertEqual(called, [])

    def test_live_result_is_timestamped_and_marked_live(self):
        adapter = WeatherAdapter("test", lambda loc: {"temp_c": 19})
        result = adapter.get(self.location, location_consent=True, now=self.now)
        self.assertEqual(result.freshness, "live")
        self.assertEqual(result.observed_at_utc, self.now.isoformat())
        self.assertEqual(result.data["temp_c"], 19)

    def test_offline_cache_is_marked_stale_not_live(self):
        calls = iter([{"condition": "rain"}, OSError("offline")])
        def fetch(_):
            item = next(calls)
            if isinstance(item, Exception):
                raise item
            return item
        adapter = WeatherAdapter("test", fetch, max_age_seconds=60)
        adapter.get(self.location, location_consent=True, now=self.now)
        result = adapter.get(self.location, location_consent=True, now=self.now + timedelta(minutes=5))
        self.assertEqual(result.freshness, "stale")
        self.assertEqual(result.data["condition"], "rain")

    def test_recent_cache_is_labelled_cached(self):
        calls = iter([{"vehicles_per_hour": 120}, OSError("temporary")])
        def fetch(_):
            item = next(calls)
            if isinstance(item, Exception):
                raise item
            return item
        adapter = TrafficAdapter("test", fetch, max_age_seconds=600)
        adapter.get(self.location, location_consent=True, now=self.now)
        result = adapter.get(self.location, location_consent=True, now=self.now + timedelta(minutes=2))
        self.assertEqual(result.freshness, "cached")

    def test_no_cache_and_provider_failure_is_unavailable(self):
        adapter = TrafficAdapter("test", lambda _: (_ for _ in ()).throw(OSError("offline")))
        with self.assertRaises(ProviderUnavailable):
            adapter.get(self.location, location_consent=True, now=self.now)

    def test_invalid_coordinates_are_rejected(self):
        adapter = WeatherAdapter("test", lambda _: {})
        with self.assertRaises(ValueError):
            adapter.get(Location(91, 0), location_consent=True, now=self.now)


if __name__ == "__main__":
    unittest.main()
