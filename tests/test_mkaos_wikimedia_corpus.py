from __future__ import annotations

import hashlib
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mkaos" / "prepare_wikimedia_corpus.py"
SPEC = importlib.util.spec_from_file_location("prepare_wikimedia_corpus", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class CorpusPreparationTests(unittest.TestCase):
    def test_document_split_is_deterministic_and_has_only_known_values(self):
        first = MODULE.document_split("123456")
        self.assertEqual(first, MODULE.document_split("123456"))
        self.assertIn(first, {"train", "validation", "test"})

    def test_document_split_is_approximately_90_5_5_on_many_documents(self):
        counts = {"train": 0, "validation": 0, "test": 0}
        for page_id in range(10_000):
            counts[MODULE.document_split(str(page_id))] += 1
        self.assertGreater(counts["train"], 8_700)
        self.assertLess(counts["train"], 9_300)
        self.assertGreater(counts["validation"], 400)
        self.assertLess(counts["validation"], 600)
        self.assertGreater(counts["test"], 400)
        self.assertLess(counts["test"], 600)

    def test_exact_duplicate_digest_ignores_whitespace_and_case(self):
        self.assertEqual(
            MODULE.content_digest("Türkçe   metin\nörneği"),
            MODULE.content_digest("türkçe metin örneği"),
        )

    def test_email_and_phone_like_strings_are_masked(self):
        text, count = MODULE.redact_contact_details("İletişim: deneme@example.org, +90 212 555 12 12")
        self.assertEqual(count, 2)
        self.assertNotIn("deneme@example.org", text)
        self.assertNotIn("+90 212 555 12 12", text)

    def test_archive_hash_function_matches_known_bytes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.bin"
            path.write_bytes(b"mkaos")
            self.assertEqual(MODULE.sha256_file(path), hashlib.sha256(b"mkaos").hexdigest())

    def test_wikitext_cleaning_keeps_turkish_unicode(self):
        try:
            import mwparserfromhell  # noqa: F401
        except ImportError:
            self.skipTest("mwparserfromhell installed by requirements-corpus.txt in CI")
        cleaned = MODULE.strip_wikitext("'''Türkçe''' [[Türkiye|Türkiye'nin]] tarihi ve ş, ğ, ı, İ.")
        self.assertIn("Türkçe", cleaned)
        self.assertIn("Türkiye'nin", cleaned)
        self.assertIn("ş, ğ, ı, İ", cleaned)


if __name__ == "__main__":
    unittest.main()
