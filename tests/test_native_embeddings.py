import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.native_embeddings import NativeHashEmbeddings
from core.rag import MemoryStore


class NativeHashEmbeddingTests(unittest.TestCase):
    def test_vectors_are_stable_normalized_and_dimension_bounded(self):
        embedder = NativeHashEmbeddings(dimensions=512)
        first = embedder.embed_query("Türkçe: arıların kış bakımı")
        second = embedder.embed_query("Türkçe: arıların kış bakımı")
        self.assertEqual(first, second)
        self.assertEqual(len(first), 512)
        self.assertAlmostEqual(math.sqrt(sum(x * x for x in first)), 1.0, places=6)
        with self.assertRaises(ValueError):
            NativeHashEmbeddings(dimensions=16)

    def test_turkish_inflection_shares_character_features(self):
        embedder = NativeHashEmbeddings(dimensions=2048)
        query = embedder.embed_query("arıların kış bakımı")
        relevant = embedder.embed_query("arılar için kış bakımını zamanında yap")
        unrelated = embedder.embed_query("borsa şirketlerinin yıllık bilanço analizi")
        cosine_relevant = sum(a * b for a, b in zip(query, relevant))
        cosine_unrelated = sum(a * b for a, b in zip(query, unrelated))
        self.assertGreater(cosine_relevant, cosine_unrelated)

    def test_rag_can_run_with_native_embeddings_without_calling_ollama(self):
        with tempfile.TemporaryDirectory() as temp:
            ollama = Mock()
            with patch.dict(os.environ, {"SEKA_EMBEDDINGS_PROVIDER": "mkaos-native"}):
                store = MemoryStore(
                    persist_directory=str(Path(temp) / "memory"),
                    collection_name="native_embedding_test",
                    ollama=ollama,
                )
                store.add_texts(
                    [
                        "Arıların kış bakımı için kovan havalandırması önemlidir.",
                        "Borsa şirketlerinin yıllık bilanço analizi finansal oranlar içerir.",
                    ],
                    [{"source": "beekeeping"}, {"source": "finance"}],
                )
                results = store.search("arılar için kış bakımını anlat", k=1)
                self.assertTrue(results)
                self.assertEqual(results[0].metadata["source"], "beekeeping")
                self.assertEqual(store.stats()["embedding_provider"], "mkaos-native")
                ollama.embeddings.assert_not_called()

    def test_unknown_embedding_provider_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"SEKA_EMBEDDINGS_PROVIDER": "remote-api"}):
                with self.assertRaisesRegex(ValueError, "SEKA_EMBEDDINGS_PROVIDER"):
                    MemoryStore(persist_directory=str(Path(temp) / "memory"))


if __name__ == "__main__":
    unittest.main()
