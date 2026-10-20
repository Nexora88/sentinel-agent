import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "prepare_trakya_environmental_dataset.py"
FIELDS = ["sample_id", "event_id", "timestamp", "latitude", "longitude", "label", "source_id"]


class TrakyaDatasetPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.registry = self.root / "registry.json"
        self.input = self.root / "observations.csv"
        self.output = self.root / "out"
        self.registry.write_text(json.dumps({"schema_version": 1, "sources": [{
            "source_id": "reviewed-source", "approval_status": "approved",
            "license": "CC BY 4.0", "source_url": "https://example.org/data",
            "access_basis": "Public dataset terms reviewed", "label_method": "Two-reviewer adjudication"
        }]}), encoding="utf-8")
        rows = [
            ["s1", "event-a", "2026-06-01T10:00:00Z", "41.2", "27.1", "fire", "reviewed-source"],
            ["s2", "event-a", "2026-06-01T10:10:00Z", "41.2", "27.1", "fire", "reviewed-source"],
            ["s3", "event-b", "2026-06-02T10:00:00Z", "41.3", "27.2", "no_fire", "reviewed-source"],
            ["s4", "event-c", "2026-06-03T10:00:00Z", "41.4", "27.3", "no_fire", "reviewed-source"],
            ["s5", "event-d", "2026-06-04T10:00:00Z", "41.5", "27.4", "fire", "reviewed-source"],
            ["s6", "event-e", "2026-06-05T10:00:00Z", "41.6", "27.5", "no_fire", "reviewed-source"],
        ]
        with self.input.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(FIELDS)
            writer.writerows(rows)

    def tearDown(self):
        self.tmp.cleanup()

    def run_pipeline(self):
        return subprocess.run([sys.executable, str(SCRIPT), "--input", str(self.input),
                               "--registry", str(self.registry), "--output-dir", str(self.output),
                               "--seed", "7"], text=True, capture_output=True, check=False)

    def test_splits_by_event_and_writes_hash_manifest(self):
        result = self.run_pipeline()
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))
        split_events = manifest["split_event_ids"]
        self.assertFalse(set(split_events["train"]) & set(split_events["validation"]))
        self.assertFalse(set(split_events["train"]) & set(split_events["test"]))
        self.assertFalse(set(split_events["validation"]) & set(split_events["test"]))
        self.assertEqual(len(manifest["input_sha256"]), 64)
        self.assertEqual(sum(manifest["counts"].values()), 6)

    def test_unapproved_source_fails_closed(self):
        data = json.loads(self.registry.read_text(encoding="utf-8"))
        data["sources"][0]["approval_status"] = "pending_review"
        self.registry.write_text(json.dumps(data), encoding="utf-8")
        result = self.run_pipeline()
        self.assertEqual(result.returncode, 2)
        self.assertIn("not approved", result.stderr)

    def test_out_of_region_coordinate_is_rejected(self):
        text = self.input.read_text(encoding="utf-8").replace('"41.2"', '"51.2"', 1)
        self.input.write_text(text, encoding="utf-8")
        result = self.run_pipeline()
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside the configured Trakya bounding box", result.stderr)


if __name__ == "__main__":
    unittest.main()
