"""Tests for offline-only semantic embeddings using a mocked local model."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from core.local_semantic_embeddings import LocalSemanticEmbeddings


class FakeSentenceTransformer:
    def __init__(self, model_path, **kwargs):
        self.model_path = model_path
        self.kwargs = kwargs

    def encode(self, texts, **kwargs):
        return [[3.0, 4.0] for _ in texts]


class LocalSemanticEmbeddingTests(unittest.TestCase):
    def test_requires_existing_local_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = str(Path(temp) / "not-installed")
            with patch.dict("os.environ", {"SEKA_LOCAL_EMBEDDING_MODEL_PATH": missing}):
                with self.assertRaisesRegex(ValueError, "does not exist"):
                    LocalSemanticEmbeddings()

    def test_loads_only_local_model_and_normalizes_output(self):
        fake_package = types.SimpleNamespace(SentenceTransformer=FakeSentenceTransformer)
        with tempfile.TemporaryDirectory() as temp, patch.dict(
            sys.modules, {"sentence_transformers": fake_package}
        ):
            embedder = LocalSemanticEmbeddings(model_path=temp)
            self.assertTrue(embedder.model.kwargs["local_files_only"])
            self.assertFalse(embedder.model.kwargs["trust_remote_code"])
            self.assertEqual(embedder.embed_query("Türkçe soru"), [3.0, 4.0])
            self.assertEqual(embedder.embed_documents(["a", "b"]), [[3.0, 4.0], [3.0, 4.0]])


if __name__ == "__main__":
    unittest.main()
