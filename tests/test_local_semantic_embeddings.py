"""Tests for offline-only semantic embeddings and model integrity verification."""
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from core.local_semantic_embeddings import LocalSemanticEmbeddings
from tools.hash_local_embedding_model import inventory_model


class FakeSentenceTransformer:
    def __init__(self, model_path, **kwargs):
        self.model_path = model_path
        self.kwargs = kwargs

    def encode(self, texts, **kwargs):
        self.encode_kwargs = kwargs
        return [[3.0, 4.0] for _ in texts]


class LocalSemanticEmbeddingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.model_dir = self.root / "model"
        self.model_dir.mkdir()
        (self.model_dir / "config.json").write_text('{"model":"local"}', encoding="utf-8")
        self.manifest_path = self.root / "inventory.json"
        self.manifest_path.write_text(
            json.dumps(inventory_model(self.model_dir)), encoding="utf-8"
        )
        self.env = patch.dict(os.environ, {
            "SEKA_LOCAL_EMBEDDING_MODEL_PATH": str(self.model_dir),
            "SEKA_LOCAL_EMBEDDING_MANIFEST": str(self.manifest_path),
            "SEKA_REQUIRE_SEMANTIC_EMBEDDINGS": "true",
            "SEKA_EMBEDDING_DEVICE": "cpu",
        }, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_requires_existing_local_directory(self):
        with patch.dict(os.environ, {"SEKA_LOCAL_EMBEDDING_MODEL_PATH": str(self.root / "missing")}):
            with self.assertRaisesRegex(ValueError, "does not exist"):
                LocalSemanticEmbeddings()

    def test_required_semantic_mode_rejects_missing_inventory(self):
        with patch.dict(os.environ, {"SEKA_LOCAL_EMBEDDING_MANIFEST": ""}):
            with self.assertRaisesRegex(ValueError, "requires SEKA_LOCAL_EMBEDDING_MANIFEST"):
                LocalSemanticEmbeddings()

    def test_model_tampering_is_rejected_before_transformer_load(self):
        (self.model_dir / "config.json").write_text('{"model":"tampered"}', encoding="utf-8")
        with patch.dict(sys.modules, {"sentence_transformers": None}):
            with self.assertRaisesRegex(ValueError, "inventory verification failed"):
                LocalSemanticEmbeddings()

    def test_loads_only_local_model_with_matching_inventory(self):
        fake_package = types.SimpleNamespace(SentenceTransformer=FakeSentenceTransformer)
        with patch.dict(sys.modules, {"sentence_transformers": fake_package}):
            embedder = LocalSemanticEmbeddings()
        self.assertTrue(embedder.model.kwargs["local_files_only"])
        self.assertFalse(embedder.model.kwargs["trust_remote_code"])
        self.assertEqual(embedder.model.kwargs["device"], "cpu")
        self.assertEqual(embedder.embed_query("Türkçe soru"), [3.0, 4.0])
        self.assertTrue(embedder.model.encode_kwargs["normalize_embeddings"])
        self.assertFalse(embedder.model.encode_kwargs["show_progress_bar"])
        self.assertEqual(embedder.embed_documents(["a", "b"]), [[3.0, 4.0], [3.0, 4.0]])


if __name__ == "__main__":
    unittest.main()
