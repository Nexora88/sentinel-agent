"""Offline-only adapter for a pre-trained semantic embedding model.

The model must already exist on disk. This module never downloads weights and
never enables remote custom code. It can require a SHA-256 inventory before
loading; a digest proves file identity, not license clearance or model quality.
"""
from __future__ import annotations

import json
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

        require_manifest = os.getenv(
            "SEKA_REQUIRE_SEMANTIC_EMBEDDINGS", "false"
        ).strip().lower() in {"1", "true", "yes", "on"}
        raw_manifest = os.getenv("SEKA_LOCAL_EMBEDDING_MANIFEST", "").strip()
        if require_manifest and not raw_manifest:
            raise ValueError(
                "SEKA_REQUIRE_SEMANTIC_EMBEDDINGS requires SEKA_LOCAL_EMBEDDING_MANIFEST "
                "to pin the exact installed model files."
            )
        if raw_manifest:
            manifest_path = Path(raw_manifest).expanduser().resolve()
            if not manifest_path.is_file():
                raise ValueError(f"Local embedding inventory manifest does not exist: {manifest_path}")
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError("Local embedding inventory manifest is unreadable or invalid JSON.") from exc
            from tools.hash_local_embedding_model import verify_inventory
            errors = verify_inventory(path, manifest)
            if errors:
                raise ValueError("Local embedding model inventory verification failed: " + "; ".join(errors[:5]))

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
