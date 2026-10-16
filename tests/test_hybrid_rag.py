"""Regression tests for bounded hybrid RAG reranking."""
import unittest

from langchain_core.documents import Document

from core.hybrid_rag import hybrid_rerank


class HybridRagTests(unittest.TestCase):
    def test_lexical_evidence_can_promote_a_candidate_from_dense_retrieval(self):
        dense_first = Document(
            page_content="Şirketin yıllık bilançosu, nakit akışı ve borçluluk oranları.",
            metadata={"source": "finance"},
        )
        lexical_match = Document(
            page_content="Arıların kış bakımı için kovan havalandırması ve besin stoğu önemlidir.",
            metadata={"source": "beekeeping"},
        )
        partial_match = Document(
            page_content="Kışın bitki sulaması ve toprak nemi kontrol edilmelidir.",
            metadata={"source": "farming"},
        )

        ranked = hybrid_rerank(
            "arıların kış bakımı ve kovan havalandırması",
            [dense_first, partial_match, lexical_match],
            limit=2,
        )
        self.assertEqual([doc.metadata["source"] for doc in ranked], ["beekeeping", "farming"])

    def test_dense_order_is_preserved_when_query_has_no_lexical_overlap(self):
        first = Document(page_content="Konu A hakkında kaynak.", metadata={"source": "a"})
        second = Document(page_content="Konu B hakkında kaynak.", metadata={"source": "b"})
        ranked = hybrid_rerank("eşsiz xyz terimi", [first, second], limit=2)
        self.assertEqual([doc.metadata["source"] for doc in ranked], ["a", "b"])

    def test_empty_input_and_bounds(self):
        self.assertEqual(hybrid_rerank("", []), [])
        with self.assertRaises(ValueError):
            hybrid_rerank("test", [Document(page_content="x")], limit=0)
        with self.assertRaises(ValueError):
            hybrid_rerank("test", [Document(page_content="x")], dense_weight=0, lexical_weight=0)

    def test_turkish_unicode_case_is_normalized(self):
        docs = [
            Document(page_content="İSTANBUL'DA KOVAN BAKIMI", metadata={"source": "turkish"}),
            Document(page_content="Finansal piyasa ve bilanço", metadata={"source": "other"}),
        ]
        ranked = hybrid_rerank("istanbul kovan bakımı", docs, limit=1)
        self.assertEqual(ranked[0].metadata["source"], "turkish")


if __name__ == "__main__":
    unittest.main()
