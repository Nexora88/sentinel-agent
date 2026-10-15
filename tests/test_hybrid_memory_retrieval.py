import threading
import unittest
from collections import OrderedDict
from unittest.mock import Mock

from langchain_core.documents import Document

from core.rag import MemoryStore


class HybridMemoryRetrievalTests(unittest.TestCase):
    def make_store(self):
        store = MemoryStore.__new__(MemoryStore)
        store.tenant_id = "tenant-a"
        store._lock = threading.RLock()
        store._search_cache = OrderedDict()
        store._search_cache_hits = 0
        store._search_cache_misses = 0
        store.vectorstore = Mock()
        return store

    def test_lexical_evidence_can_promote_exact_turkish_fact(self):
        store = self.make_store()
        broad = Document(page_content="Genel tarım takvimi ve bitki yetiştirme önerileri.", metadata={"source": "broad"})
        exact = Document(page_content="Edirne tarlasında toprak nemi ölçümü ve sulama takvimi.", metadata={"source": "exact"})
        store.vectorstore.similarity_search.return_value = [broad, exact]

        result = store.search("Edirne tarlasında toprak nemi sulama", k=2)

        self.assertEqual(result[0].metadata["source"], "exact")
        store.vectorstore.similarity_search.assert_called_once_with(
            "Edirne tarlasında toprak nemi sulama", k=12,
            filter={"tenant_id": "tenant-a"},
        )

    def test_repeated_queries_use_short_lived_cache(self):
        store = self.make_store()
        store.vectorstore.similarity_search.return_value = [
            Document(page_content="MKAOS yerel bellek notu.", metadata={"source": "notes"})
        ]

        first = store.search("MKAOS bellek", k=1)
        second = store.search("MKAOS bellek", k=1)

        self.assertEqual(first, second)
        store.vectorstore.similarity_search.assert_called_once()
        self.assertEqual(store._search_cache_hits, 1)
        self.assertEqual(store._search_cache_misses, 1)

    def test_newly_ingested_information_invalidates_cache(self):
        store = self.make_store()
        store.max_chars_per_ingest = 1000
        store.max_chunks_per_ingest = 10
        store.splitter = Mock()
        store.splitter.create_documents.return_value = [
            Document(page_content="Yeni bilgi", metadata={"source": "manual"})
        ]
        store._prune_if_needed = Mock()
        store._search_cache[("tenant-a", "eski", 1)] = (0.0, ())
        store.vectorstore.add_documents.return_value = None

        store.add_texts(["Yeni bilgi"], [{"source": "manual"}])

        self.assertEqual(len(store._search_cache), 0)
        store.vectorstore.add_documents.assert_called_once()


if __name__ == "__main__":
    unittest.main()
