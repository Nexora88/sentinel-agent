"""Offline tests for MKAOS from-scratch corpus integrity gates."""
from __future__ import annotations

import hashlib
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "train_mkaos_from_scratch.py"
SPEC = importlib.util.spec_from_file_location("mkaos_from_scratch", SCRIPT)
assert SPEC and SPEC.loader
TRAINER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRAINER)


def record(sample_id: str, text: str, split: str) -> dict[str, str]:
    return {
        "sample_id": sample_id,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "split": split,
    }


class CorpusIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = {"tr": "Türkçe", "val": "Doğrulama", "test": "Ayrık test"}
        self.manifest = {"records": [
            record("tr", self.corpus["tr"], "train"),
            record("val", self.corpus["val"], "validation"),
            record("test", self.corpus["test"], "test"),
        ]}

    def test_approved_manifest_content_maps_to_splits(self) -> None:
        splits = TRAINER.validate_corpus_against_manifest(self.corpus, self.manifest)
        self.assertEqual(splits["train"], ["Türkçe"])
        self.assertEqual(splits["validation"], ["Doğrulama"])
        self.assertEqual(splits["test"], ["Ayrık test"])

    def test_changed_text_is_rejected(self) -> None:
        corpus = dict(self.corpus)
        corpus["tr"] = "İzinsiz değiştirilmiş metin"
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            TRAINER.validate_corpus_against_manifest(corpus, self.manifest)

    def test_unmanifested_text_is_rejected(self) -> None:
        corpus = {**self.corpus, "extra": "manifest dışı"}
        with self.assertRaisesRegex(ValueError, "absent from manifest"):
            TRAINER.validate_corpus_against_manifest(corpus, self.manifest)

    def test_missing_held_out_split_is_rejected(self) -> None:
        manifest = {"records": self.manifest["records"][:2]}
        # Fail-closed validation detects the unmanifested test sample before split completeness.
        corpus = {key: value for key, value in self.corpus.items() if key != "test"}
        with self.assertRaisesRegex(ValueError, "Missing non-empty split"):
            TRAINER.validate_corpus_against_manifest(corpus, manifest)

    def test_duplicate_manifest_id_is_rejected(self) -> None:
        manifest = {"records": self.manifest["records"] + [self.manifest["records"][0]]}
        with self.assertRaisesRegex(ValueError, "duplicate manifest sample_id"):
            TRAINER.validate_corpus_against_manifest(self.corpus, manifest)


if __name__ == "__main__":
    unittest.main()
