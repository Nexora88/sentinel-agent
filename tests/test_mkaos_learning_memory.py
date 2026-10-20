import tempfile
import unittest
from pathlib import Path

from tools.mkaos_learning_memory import load_json, update_memory, write_json_atomic


class MkaosLearningMemoryTests(unittest.TestCase):
    def report(self, status="failed", include_check=True):
        checks = {"python_tests": {"status": status, "exit_code": 1 if status == "failed" else 0}}
        return {
            "project": "MKAOS",
            "commit_sha": "abc123",
            "projects": [{"id": "demo", "status": "failed" if status == "failed" else "completed",
                          "checks": checks if include_check else {}}],
        }

    def test_failure_is_remembered_without_raw_logs(self):
        memory = update_memory(None, self.report(), now="2026-10-20T00:00:00+00:00")
        self.assertEqual(memory["summary"]["current_failure_fingerprints"], 1)
        entry = memory["entries"][0]
        self.assertTrue(entry["regression_test_required"])
        self.assertIn("Reproduce the failure", entry["regression_test_guidance"])
        self.assertNotIn("stdout", entry)
        self.assertNotIn("stderr", entry)

    def test_repeated_failure_increments_occurrences(self):
        first = update_memory(None, self.report(), now="2026-10-20T00:00:00+00:00")
        second = update_memory(first, self.report(), now="2026-10-21T00:00:00+00:00")
        self.assertEqual(second["entries"][0]["occurrences"], 2)
        self.assertEqual(second["rechecked_history"][0]["result"], "recurring_failure")

    def test_passed_check_marks_old_failure_cleared_only_after_recheck(self):
        first = update_memory(None, self.report(), now="2026-10-20T00:00:00+00:00")
        second = update_memory(first, self.report(status="passed"), now="2026-10-21T00:00:00+00:00")
        entry = next(x for x in second["entries"] if x["check"] == "python_tests")
        self.assertEqual(entry["last_status"], "cleared_on_recheck")
        self.assertIn("last_rechecked_utc", entry)

    def test_unavailable_check_is_not_mistaken_for_a_fix(self):
        first = update_memory(None, self.report(), now="2026-10-20T00:00:00+00:00")
        unavailable = self.report(status="unavailable")
        second = update_memory(first, unavailable, now="2026-10-21T00:00:00+00:00")
        entry = next(x for x in second["entries"] if x["check"] == "python_tests")
        self.assertEqual(entry["last_status"], "still_unverified")

    def test_memory_write_is_atomic_and_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "memory.json"
            memory = update_memory(None, self.report(), now="2026-10-20T00:00:00+00:00")
            write_json_atomic(path, memory)
            self.assertEqual(load_json(path)["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
