from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from tools.extract_common_voice_text import extract, normalize, split_for_group


class CommonVoiceTextExtractorTests(unittest.TestCase):
    def test_normalization_collapses_case_and_whitespace(self) -> None:
        self.assertEqual(normalize("  İSTANBUL  güzel\tşehir "), normalize("İstanbul güzel şehir"))

    def test_split_is_deterministic_and_uses_three_buckets(self) -> None:
        self.assertEqual(split_for_group("12345678"), split_for_group("12345678"))
        self.assertEqual(split_for_group("00000050"), "validation")
        self.assertEqual(split_for_group("00000000"), "train")
        self.assertEqual(split_for_group("0000005a"), "test")

    def test_extracts_text_only_deduplicates_and_keeps_review_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            # Common Voice sentence metadata, not the clips/validated.tsv participant table.
            path = Path(temp) / "sentences.tsv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["sentence", "source", "client_id"],
                    delimiter="\t",
                )
                writer.writeheader()
                writer.writerow({
                    "sentence": "Merhaba dünya.",
                    "source": "review-pending-source-A",
                    "client_id": "must-not-leak",
                })
                writer.writerow({
                    "sentence": "  MERHABA   DÜNYA. ",
                    "source": "review-pending-source-B",
                    "client_id": "must-not-leak-either",
                })
                writer.writerow({
                    "sentence": "Bugün hava güzel.",
                    "source": "review-pending-source-A",
                    "client_id": "not-retained",
                })
            rows, report = extract(
                path,
                release="Scripted Speech v27.0 Turkish",
                source_uri="https://commonvoice.mozilla.org/datasets",
            )
            self.assertEqual(len(rows), 2)
            self.assertEqual(report["duplicate_normalized_sentences_removed"], 1)
            self.assertEqual(report["input_file_sha256"], __import__("hashlib").sha256(path.read_bytes()).hexdigest())
            self.assertTrue(all(row["human_review"] == "pending" for row in rows))
            self.assertTrue(all(row["pii_status"] == "unknown" for row in rows))
            self.assertTrue(all(row["source_file_sha256"] == report["input_file_sha256"] for row in rows))
            self.assertNotIn("client_id", repr(rows))
            self.assertFalse(report["training_allowed"])
            self.assertFalse(report["audio_read_or_copied"])
            # Duplicate normalized text retains every source label rather than silently losing provenance.
            duplicate = next(
                row for row in rows
                if normalize(row["text"]) == normalize("Merhaba dünya.")
            )
            self.assertEqual(
                duplicate["all_observed_source_labels"],
                ["review-pending-source-A", "review-pending-source-B"],
            )


if __name__ == "__main__":
    unittest.main()
