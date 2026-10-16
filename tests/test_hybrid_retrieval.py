"""Tests for deterministic local-only hybrid RAG ranking."""
from __future__ import annotations

import unittest
from dataclasses import dataclass

from core.hybrid_retrieval import rerank_local_candidates, tokenize


@dataclass
class Document:
    page_content: str


class HybridRetrievalTests(unittest.TestCase):
    def test_turkish_case_normalization_preserves_dotless_i(self):
        self.assertEqual(tokenize("IŞIK ve İSTANBUL"), ["ışık", "ve", "istanbul"])

    def test_lexical_evidence_can_promote_exact_answer(self):
        vector_order = [
            Document("Borsa bilanço ve şirket finansal oranları."),
            Document("Arıların kış bakımı: kovan havalandırması ve besleme."),
            Document("Genel bir bahçe notu."),
        ]
        ranked = rerank_local_candidates("arıların kış bakımı", vector_order, 2)
        self.assertEqual(ranked[0].page_content, vector_order[1].page_content)

    def test_empty_query_and_empty_candidates_are_safe(self):
        docs = [Document("Yerel not")]
        self.assertEqual(rerank_local_candidates("  ", docs, 5), [])
        self.assertEqual(rerank_local_candidates("soru", [], 5), [])
        self.assertEqual(rerank_local_candidates("soru", docs, 0), [])

    def test_repeated_calls_have_stable_tie_breaking(self):
        docs = [Document("ortak not"), Document("ortak kayıt"), Document("başka")]
        first = rerank_local_candidates("eşleşmeyen sorgu", docs, 3)
        second = rerank_local_candidates("eşleşmeyen sorgu", docs, 3)
        self.assertEqual([d.page_content for d in first], [d.page_content for d in second])

    def test_no_network_or_embedding_provider_is_required(self):
        docs = [Document("Trakya tarlalarında toprak nemi sulama kararını etkiler.")]
        self.assertEqual(rerank_local_candidates("toprak nemi sulama", docs, 1), docs)


if __name__ == "__main__":
    unittest.main()
