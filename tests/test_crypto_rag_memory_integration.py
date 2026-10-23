import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.rag import MemoryStore


class CryptoRAGMemoryIntegrationTests(unittest.TestCase):
    def test_memory_store_uses_encrypted_backend_and_preserves_tenant_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "chroma"
            encrypted_path = root / "crypto-rag" / "vectors.sqlite3"
            env = {
                "SEKA_EMBEDDINGS_PROVIDER": "mkaos-native",
                "SEKA_REQUIRE_SEMANTIC_EMBEDDINGS": "false",
                "SEKA_RAG_STORAGE_BACKEND": "crypto-sqlite",
                "SEKA_CRYPTO_RAG_PATH": str(encrypted_path),
                "MKAOS_CRYPTO_RAG_KEY": base64.b64encode(b"k" * 32).decode("ascii"),
                "SEKA_RAG_HYBRID_RERANK": "false",
            }
            with patch.dict(os.environ, env):
                owner = MemoryStore(persist_directory=str(source_dir), tenant_id="tenant-a")
                self.assertEqual(owner.storage_backend, "crypto-sqlite")
                self.assertEqual(owner.add_texts(["private local memory about forests"], metadatas=[{"source": "note-a"}]), 1)
                found = owner.search("private forest memory", k=3)
                self.assertEqual(len(found), 1)
                self.assertIn("private local memory", found[0].page_content)
                self.assertEqual(owner.stats()["documents"], 1)
                self.assertEqual(owner.stats()["storage_backend"], "crypto-sqlite")
                self.assertFalse(any(source_dir.rglob("*")), "Crypto-RAG must not create Chroma plaintext records")

                reopened = MemoryStore(persist_directory=str(source_dir), tenant_id="tenant-a")
                self.assertEqual(len(reopened.search("private forest memory")), 1)
                other_tenant = MemoryStore(persist_directory=str(source_dir), tenant_id="tenant-b")
                self.assertEqual(other_tenant.search("private forest memory"), [])

    def test_encrypted_backend_prunes_to_configured_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {
                "SEKA_EMBEDDINGS_PROVIDER": "mkaos-native",
                "SEKA_REQUIRE_SEMANTIC_EMBEDDINGS": "false",
                "SEKA_RAG_STORAGE_BACKEND": "crypto-sqlite",
                "SEKA_CRYPTO_RAG_PATH": str(root / "crypto-rag" / "vectors.sqlite3"),
                "MKAOS_CRYPTO_RAG_KEY": base64.b64encode(b"z" * 32).decode("ascii"),
                "SEKA_RAG_HYBRID_RERANK": "false",
            }
            with patch.dict(os.environ, env):
                store = MemoryStore(persist_directory=str(root / "chroma"), max_documents=1)
                store.add_texts(["first stored note", "second stored note"], metadatas=[{"source": "one"}, {"source": "two"}])
                self.assertEqual(store.stats()["documents"], 1)

    def test_crypto_backend_rejects_ollama_before_initializing_client(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "SEKA_EMBEDDINGS_PROVIDER": "ollama",
                "SEKA_REQUIRE_SEMANTIC_EMBEDDINGS": "false",
                "SEKA_RAG_STORAGE_BACKEND": "crypto-sqlite",
            }
            with patch.dict(os.environ, env, clear=False):
                with patch("core.rag.OllamaClient", side_effect=AssertionError("must not initialize Ollama")):
                    with self.assertRaises(ValueError):
                        MemoryStore(persist_directory=str(Path(tmp) / "chroma"))

    def test_crypto_backend_requires_explicit_path_and_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "SEKA_EMBEDDINGS_PROVIDER": "mkaos-native",
                "SEKA_REQUIRE_SEMANTIC_EMBEDDINGS": "false",
                "SEKA_RAG_STORAGE_BACKEND": "crypto-sqlite",
            }
            with patch.dict(os.environ, env, clear=False):
                os.environ.pop("SEKA_CRYPTO_RAG_PATH", None)
                os.environ.pop("MKAOS_CRYPTO_RAG_KEY", None)
                with self.assertRaises(ValueError):
                    MemoryStore(persist_directory=str(Path(tmp) / "chroma"))


if __name__ == "__main__":
    unittest.main()
