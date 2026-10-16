"""Offline-only adapter for a pre-trained semantic embedding model.

The model must already exist on disk. This module never downloads weights and
never enables remote custom code. It improves semantic retrieval only when a
compatible local model has been installed and evaluated for the target corpus.
"""
from __future__ import annotations

import os
from pathlib import Path

from langchain_core.embeddings import Embeddings


class LocalSemanticEmbeddings(Embeddings):
    """Sentence-Transformers adapter constrained to a pre-existing local path."""

    def __init__(self, model_path: str | None = None, device: str | None = None):
        raw_path = model_path or os.getenv("SEKA_LOCAL_EMBEDDING_MODEL_PATH", "")
        if not raw_path.strip():
            raise ValueError(
                "SEKA_LOCAL_EMBEDDING_MODEL_PATH must point to an already-installed local model directory."
            )
        path = Path(raw_path).expanduser().resolve()
        if not path.is_dir():
            raise ValueError(f"Local embedding model directory does not exist: {path}")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional sentence-transformers package to use local-semantic embeddings."
            ) from exc
        # Explicitly offline: no remote model IDs and no arbitrary model Python code.
        self.model = SentenceTransformer(
            str(path),
            device=device or os.getenv("SEKA_EMBEDDING_DEVICE", "cpu"),
            local_files_only=True,
            trust_remote_code=False,
        )
        self.model_path = str(path)

    def _encode(self, texts: list[str]) -> list[list[float]]:
        if any(not isinstance(text, str) for text in texts):
            raise TypeError("Embedding inputs must be strings.")
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [[float(value) for value in vector] for vector in vectors]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([text])[0]
