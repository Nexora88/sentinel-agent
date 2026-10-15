import tempfile
import threading
import unittest
from pathlib import Path

from core.night_scheduler import NightScheduler


class NightSchedulerTests(unittest.TestCase):
    def test_cycle_persists_success_without_saving_full_private_result(self):
        with tempfile.TemporaryDirectory() as directory:
            scheduler = NightScheduler(
                lambda: {"summary": "Türkçe test raporu", "private_payload": "do-not-store"},
                enabled=False,
                state_path=str(Path(directory) / "night.json"),
            )
            result = scheduler.run_cycle()
            saved = Path(directory, "night.json").read_text(encoding="utf-8")
            self.assertEqual(result["status"], "success")
            self.assertIn("Türkçe test raporu", saved)
            self.assertNotIn("do-not-store", saved)
            self.assertEqual(scheduler.status()["enabled"], False)

    def test_failed_cycle_is_recorded_and_exception_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as directory:
            def fail():
                raise ConnectionError("local model offline")

            scheduler = NightScheduler(fail, state_path=str(Path(directory) / "night.json"))
            with self.assertRaises(ConnectionError):
                scheduler.run_cycle()
            state = scheduler.status()["last_run"]
            self.assertEqual(state["status"], "error")
            self.assertEqual(state["error"], "ConnectionError")

    def test_overlapping_cycle_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            scheduler = NightScheduler(lambda: {"summary": "ok"}, state_path=str(Path(directory) / "night.json"))
            self.assertTrue(scheduler._run_lock.acquire(blocking=False))
            try:
                with self.assertRaisesRegex(RuntimeError, "zaten çalışıyor"):
                    scheduler.run_cycle()
            finally:
                scheduler._run_lock.release()

    def test_invalid_schedule_time_is_rejected(self):
        with self.assertRaises(ValueError):
            NightScheduler(lambda: {}, hour=24)


if __name__ == "__main__":
    unittest.main()
