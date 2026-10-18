"""Tests for the fail-closed MKAOS source register validator."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from tools.validate_mkaos_source_register import FIELDS, validate_register


class SourceRegisterTests(unittest.TestCase):
    def write_rows(self, root: Path, rows: list[dict[str, str]]) -> Path:
        path = root / "register.tsv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def valid_row(self) -> dict[str, str]:
        return {
            "source_id": "src-001",
            "source_uri": "https://example.org/dataset",
            "source_type": "licensed-corpus",
            "version_or_snapshot": "v1",
            "acquired_at_utc": "2026-10-15T12:00:00Z",
            "license_id": "CC-BY-4.0",
            "license_evidence_uri": "https://example.org/license",
            "attribution_requirement": "required",
            "attribution_evidence_uri": "https://example.org/attribution-review",
            "training_permission": "yes",
            "redistribution_permission": "no",
            "privacy_review": "passed",
            "privacy_evidence_uri": "local-archive://reviews/privacy/src-001",
            "reviewer_id": "reviewer-1",
            "review_date": "2026-10-16",
            "decision": "approved",
            "notes": "synthetic test fixture only",
        }

    def test_empty_template_is_valid_but_not_approved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_rows(Path(temp), [])
            errors, count, approved = validate_register(path)
        self.assertEqual(errors, [])
        self.assertEqual((count, approved), (0, 0))

    def test_complete_approved_record_passes_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_rows(Path(temp), [self.valid_row()])
            errors, count, approved = validate_register(path)
        self.assertEqual(errors, [])
        self.assertEqual((count, approved), (1, 1))

    def test_approved_source_without_privacy_pass_is_rejected(self) -> None:
        row = self.valid_row()
        row["privacy_review"] = "not-reviewed"
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_rows(Path(temp), [row])
            errors, _, _ = validate_register(path)
        self.assertTrue(any("privacy_review=passed" in error for error in errors))

    def test_approved_source_without_training_permission_is_rejected(self) -> None:
        row = self.valid_row()
        row["training_permission"] = "unknown"
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_rows(Path(temp), [row])
            errors, _, _ = validate_register(path)
        self.assertTrue(any("training_permission=yes" in error for error in errors))

    def test_duplicate_source_ids_are_rejected(self) -> None:
        row = self.valid_row()
        duplicate = dict(row)
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_rows(Path(temp), [row, duplicate])
            errors, _, _ = validate_register(path)
        self.assertTrue(any("duplicate source_id" in error for error in errors))

    def test_missing_license_evidence_blocks_approval(self) -> None:
        row = self.valid_row()
        row["license_evidence_uri"] = ""
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_rows(Path(temp), [row])
            errors, _, _ = validate_register(path)
        self.assertTrue(any("missing license_evidence_uri" in error for error in errors))

    def test_approved_source_requires_attribution_and_privacy_evidence(self) -> None:
        row = self.valid_row()
        row["attribution_requirement"] = "unknown"
        row["attribution_evidence_uri"] = ""
        row["privacy_evidence_uri"] = ""
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_rows(Path(temp), [row])
            errors, _, _ = validate_register(path)
        self.assertTrue(any("attribution decision" in error for error in errors))
        self.assertTrue(any("attribution evidence" in error for error in errors))
        self.assertTrue(any("privacy review evidence" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
