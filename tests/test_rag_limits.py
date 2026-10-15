import threading
import unittest
from unittest.mock import Mock

from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.rag import MemoryStore, _limit


class BoundedRagTests(unittest.TestCase):
    def make_store(self, *, max_docs=10, max_chunks=4, max_chars=1000):
        store = MemoryStore.__new__(MemoryStore)
        store.max_documents = max_docs
        store.max_chunks_per_ingest = max_chunks
        store.max_chars_per_ingest = max_chars
        store._lock = threading.RLock()
        store.splitter = RecursiveCharacterTextSplitter(
            chunk_size=10, chunk_overlap=0, separators=[" "]
        )
        store.vectorstore = Mock()
        store.vectorstore._collection.count.return_value = 0
        store.vectorstore._collection.get.return_value = {"ids": [], "metadatas": []}
        return store

    def test_document_limit_has_a_hard_memory_safety_ceiling(self):
        self.assertEqual(_limit(1_000_000, "SEKA_RAG_MAX_DOCUMENTS", 10_000, 100_000), 100_000)

    def test_rejects_oversized_ingest_before_any_write(self):
        store = self.make_store(max_chars=5)
        with self.assertRaisesRegex(ValueError, "karakter sınırını"):
            store.add_texts(["123456"])
        store.vectorstore.add_documents.assert_not_called()

    def test_rejects_too_many_chunks_before_any_write(self):
        store = self.make_store(max_chunks=2)
        with self.assertRaisesRegex(ValueError, "bilgi parçası"):
            store.add_texts(["a b c d e f g h i j k l"])
        store.vectorstore.add_documents.assert_not_called()

    def test_ids_are_stable_for_duplicate_source_chunks(self):
        store = self.make_store()
        store.add_texts(["same text"], [{"source": "notes.txt", "type": "text"}])
        first_ids = store.vectorstore.add_documents.call_args.kwargs["ids"]
        store.vectorstore.reset_mock()
        store.add_texts(["same text"], [{"source": "notes.txt", "type": "text"}])
        second_ids = store.vectorstore.add_documents.call_args.kwargs["ids"]
        self.assertEqual(first_ids, second_ids)

    def test_prunes_oldest_items_to_configured_cap(self):
        store = self.make_store(max_docs=3)
        collection = store.vectorstore._collection
        collection.count.return_value = 5
        collection.get.return_value = {
            "ids": ["a", "b", "c", "d", "e"],
            "metadatas": [
                {"created_at": "2020"}, {"created_at": "2021"},
                {"created_at": "2022"}, {"created_at": "2023"},
                {"created_at": "2024"},
            ],
        }
        store.add_texts(["fresh"])
        collection.delete.assert_called_once_with(ids=["a", "b"])

    def test_search_failure_degrades_to_empty_memory(self):
        store = self.make_store()
        store.vectorstore.similarity_search.side_effect = RuntimeError("local index unavailable")
        self.assertEqual(store.search("Türkçe soru"), [])


if __name__ == "__main__":
    unittest.main()
