import os
import unittest
from unittest.mock import Mock, patch

from core.live_data import LiveDataError, get_traffic, get_weather


class LiveDataTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "MKAOS_NETWORK_MODE": "networked",
            "ALLOW_LIVE_WEATHER": "true",
            "ALLOW_LIVE_TRAFFIC": "true",
            "TOMTOM_API_KEY": "test-only-not-a-real-key",
        })
        self.env.start()
        from core import live_data
        with live_data._lock:
            live_data._cache.clear()

    def tearDown(self):
        self.env.stop()

    def test_weather_uses_real_provider_timestamp_and_cache(self):
        response = Mock()
        response.json.return_value = {
            "timezone": "UTC",
            "current_units": {"temperature_2m": "°C"},
            "current": {"time": "2026-10-21T10:00", "temperature_2m": 14.2},
        }
        response.raise_for_status.return_value = None
        with patch("core.live_data.requests.get", return_value=response) as get:
            first = get_weather(41.0, 29.0)
            second = get_weather(41.0, 29.0)
        self.assertEqual(first["provider"], "Open-Meteo")
        self.assertEqual(first["observed_at"], "2026-10-21T10:00")
        self.assertEqual(first["current"]["temperature_2m"], 14.2)
        self.assertEqual(second["cache"], "hit")
        self.assertEqual(get.call_count, 1)

    def test_weather_is_blocked_without_explicit_opt_in(self):
        with patch.dict(os.environ, {"MKAOS_NETWORK_MODE": "offline"}):
            with self.assertRaises(LiveDataError):
                get_weather(41, 29)

    def test_invalid_coordinates_are_rejected(self):
        with self.assertRaises(LiveDataError):
            get_weather(120, 29)

    def test_traffic_does_not_expose_api_key(self):
        response = Mock()
        response.json.return_value = {"flowSegmentData": {"currentSpeed": 30, "freeFlowSpeed": 50, "confidence": 0.8}}
        response.raise_for_status.return_value = None
        with patch("core.live_data.requests.get", return_value=response) as get:
            result = get_traffic(41, 29)
        self.assertEqual(result["provider"], "TomTom Traffic Flow")
        self.assertEqual(result["current"]["current_speed"], 30)
        self.assertNotIn("test-only-not-a-real-key", str(result))
        self.assertEqual(get.call_args.kwargs["params"]["key"], "test-only-not-a-real-key")

    def test_traffic_requires_api_key(self):
        with patch.dict(os.environ, {"TOMTOM_API_KEY": ""}):
            with self.assertRaises(LiveDataError):
                get_traffic(41, 29)


if __name__ == "__main__":
    unittest.main()
