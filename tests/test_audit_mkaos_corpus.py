import json
import tempfile
import unittest
from pathlib import Path

from tools.audit_mkaos_corpus import audit, digest


def manifest_row(sample_id, text, split):
    return {
        "sample_id": sample_id, "source_id": "first-party", "source_uri": "https://example.org/source",
        "license_id": "CC0-1.0", "consent": "open_license", "sha256": digest(text),
        "language": "tr", "topic": "software", "human_review": "approved",
        "pii_status": "cleared", "split": split,
    }


class MkaosCorpusAuditTests(unittest.TestCase):
    def test_reports_bytes_splits_and_passes_clean_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                {"sample_id": "a", "text": "Türkçe kod"},
                {"sample_id": "b", "text": "Savunmacı analiz"},
                {"sample_id": "c", "text": "Güvenli test"},
            ]
            (root / "corpus.jsonl").write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
            )
            manifest = {
                "schema_version": 1, "dataset_id": "test", "revision": "1",
                "created_at": "2026-10-17", "curator": "reviewed", "license_reviewed": True,
                "records": [
                    manifest_row("a", rows[0]["text"], "train"),
                    manifest_row("b", rows[1]["text"], "validation"),
                    manifest_row("c", rows[2]["text"], "test"),
                ],
            }
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            report = audit(root / "corpus.jsonl", root / "manifest.json")
            self.assertEqual(report["quality_gate"], "pass")
            self.assertEqual(report["valid_records"], 3)
            self.assertEqual(report["split_record_counts"], {"train": 1, "validation": 1, "test": 1})
            self.assertGreater(report["byte_tokens_including_eos_estimate"], 0)

    def test_detects_normalized_duplicates_and_split_leakage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                {"sample_id": "a", "text": "Merhaba   dünya"},
                {"sample_id": "b", "text": " merhaba dünya "},
                {"sample_id": "c", "text": "başka örnek"},
            ]
            (root / "corpus.jsonl").write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
            )
            manifest = {
                "schema_version": 1, "dataset_id": "test", "revision": "1",
                "created_at": "2026-10-17", "curator": "reviewed", "license_reviewed": True,
                "records": [
                    manifest_row("a", rows[0]["text"], "train"),
                    manifest_row("b", rows[1]["text"], "test"),
                    manifest_row("c", rows[2]["text"], "validation"),
                ],
            }
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            report = audit(root / "corpus.jsonl", root / "manifest.json")
            self.assertEqual(report["quality_gate"], "fail")
            self.assertEqual(report["normalized_duplicate_records"], 1)
            self.assertEqual(report["cross_split_normalized_leaks"], 1)


if __name__ == "__main__":
    unittest.main()
