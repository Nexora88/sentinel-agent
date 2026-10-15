"""Integration regression tests for isolated tenant RAG and personal memory."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from langchain_core.embeddings import Embeddings
from core.rag import MemoryStore
from core.personal_memory import PersonalMemory

class DeterministicEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [[float((sum(map(ord, text)) % 101) + 1), 1.0, 0.5] for text in texts]
    def embed_query(self, text):
        return [float((sum(map(ord, text)) % 101) + 1), 1.0, 0.5]

class TenantMemoryIsolationTests(unittest.TestCase):
    def test_rag_directories_and_search_are_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            embedder = DeterministicEmbeddings()
            ollama = SimpleNamespace(embeddings=embedder)
            alice = MemoryStore(persist_directory=str(Path(temp) / "alice"), tenant_id="alice", ollama=ollama)
            bob = MemoryStore(persist_directory=str(Path(temp) / "bob"), tenant_id="bob", ollama=ollama)
            alice.add_texts(["alice private research phrase"], [{"source": "unit-test"}])
            self.assertTrue(alice.search("alice private research phrase"))
            self.assertEqual(bob.search("alice private research phrase"), [])
            self.assertNotEqual(alice.persist_directory, bob.persist_directory)

    def test_profiles_and_personal_vectors_are_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            embedder = DeterministicEmbeddings()
            ollama = SimpleNamespace(embeddings=embedder)
            alice = PersonalMemory(str(Path(temp) / "alice"), ollama=ollama, tenant_id="alice")
            bob = PersonalMemory(str(Path(temp) / "bob"), ollama=ollama, tenant_id="bob")
            alice.add_fact("alice confidential preference")
            self.assertEqual(alice.profile["facts"], ["alice confidential preference"])
            self.assertEqual(bob.profile["facts"], [])
            self.assertTrue(alice.search("alice confidential preference"))
            self.assertEqual(bob.search("alice confidential preference"), [])
            self.assertNotEqual(alice.profile_path, bob.profile_path)

if __name__ == "__main__":
    unittest.main()
