"""
Bounded local RAG memory for SEKA.

All vector data stays in the configured local Chroma persistence directory.
Ingestion is bounded, IDs are deterministic for de-duplication, and old chunks
are pruned to a configured maximum. A corrupt/unavailable store is never reset.
"""
from __future__ import annotations

import hashlib
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.ollama_client import OllamaClient

logger = logging.getLogger("seka.rag")


def _limit(value: Optional[int], env_name: str, default: int, ceiling: int) -> int:
    raw = value if value is not None else os.getenv(env_name, str(default))
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, ceiling))


class MemoryStore:
    """Persistent, bounded local vector memory."""

    def __init__(
        self,
        collection_name: str = "sentinel_memory",
        persist_directory: str = "./memory",
        ollama: Optional[OllamaClient] = None,
        max_documents: Optional[int] = None,
        max_chunks_per_ingest: Optional[int] = None,
        max_chars_per_ingest: Optional[int] = None,
        tenant_id: Optional[str] = None,
    ):
        self.tenant_id = str(tenant_id).strip().lower() if tenant_id else None
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        # Native n-gram hashing is a transparent offline baseline, not semantic understanding.
        # For semantic retrieval, opt into a pre-installed local model; downloads are disabled.
        self.embedding_provider = os.getenv("SEKA_EMBEDDINGS_PROVIDER", "mkaos-native").strip().lower()
        if self.embedding_provider == "mkaos-native":
            from core.native_embeddings import NativeHashEmbeddings
            embedding_function = NativeHashEmbeddings()
            self.ollama = ollama  # Do not construct or contact a model server in native mode.
        elif self.embedding_provider == "local-semantic":
            from core.local_semantic_embeddings import LocalSemanticEmbeddings
            embedding_function = LocalSemanticEmbeddings()
            self.ollama = ollama  # The semantic model is loaded from disk; no server is contacted.
        elif self.embedding_provider == "ollama":
            self.ollama = ollama or OllamaClient()
            embedding_function = self.ollama.embeddings
        else:
            raise ValueError("SEKA_EMBEDDINGS_PROVIDER must be ollama, mkaos-native, or local-semantic")
        self.collection_name = collection_name
        # Never mix vectors produced by different embedding spaces, even if dimensions match.
        suffixes = {
            "mkaos-native": "_native_hash_v1",
            "local-semantic": "_local_semantic_v1",
            "ollama": "_ollama",
        }
        provider_suffix = suffixes[self.embedding_provider]
        base_name = collection_name[:63 - len(provider_suffix)].rstrip("-_") or "seka"
        self.storage_collection_name = base_name + provider_suffix
        self.max_documents = _limit(max_documents, "SEKA_RAG_MAX_DOCUMENTS", 10000, 100000)
        self.max_chunks_per_ingest = _limit(
            max_chunks_per_ingest, "SEKA_RAG_MAX_CHUNKS_PER_INGEST", 500, 10000
        )
        self.max_chars_per_ingest = _limit(
            max_chars_per_ingest, "SEKA_RAG_MAX_CHARS_PER_INGEST", 1000000, 10000000
        )
        self._lock = threading.RLock()
        self.vectorstore = Chroma(
            collection_name=self.storage_collection_name,
            embedding_function=embedding_function,
            persist_directory=str(self.persist_directory),
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n\n", "\n", " ", ""],
        )

    @staticmethod
    def _safe_metadata(metadata: dict) -> dict:
        safe = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                safe[str(key)[:128]] = value
            else:
                safe[str(key)[:128]] = str(value)[:1000]
        safe.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        return safe

    @staticmethod
    def _document_id(document: Document) -> str:
        identity = "\0".join((
            str(document.metadata.get("source", "manual")),
            str(document.metadata.get("repo", "")),
            str(document.metadata.get("type", "text")),
            document.page_content,
        ))
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    def add_texts(self, texts: List[str], metadatas: Optional[List[dict]] = None) -> int:
        """Ingest a bounded batch; reject oversized batches instead of partial writes."""
        if not isinstance(texts, list) or not texts:
            return 0
        if any(not isinstance(text, str) for text in texts):
            raise ValueError("Bilgi deposuna yalnızca metin eklenebilir.")
        total_chars = sum(len(text) for text in texts)
        if total_chars > self.max_chars_per_ingest:
            raise ValueError(
                f"Bilgi paketi {self.max_chars_per_ingest:,} karakter sınırını aşıyor; "
                "metni daha küçük parçalara böl."
            )
        if metadatas is not None and len(metadatas) != len(texts):
            raise ValueError("Metin ve metadata sayısı eşleşmiyor.")

        metadata_rows = metadatas or [{} for _ in texts]
        docs = []
        for text, metadata in zip(texts, metadata_rows):
            if not isinstance(metadata, dict):
                raise ValueError("Bilgi metadata alanı geçersiz.")
            scoped_metadata = dict(metadata)
            tenant_id = getattr(self, "tenant_id", None)
            if tenant_id:
                scoped_metadata["tenant_id"] = tenant_id
            for document in self.splitter.create_documents([text], metadatas=[self._safe_metadata(scoped_metadata)]):
                docs.append(document)
                if len(docs) > self.max_chunks_per_ingest:
                    raise ValueError(
                        f"Tek yüklemede en fazla {self.max_chunks_per_ingest} bilgi parçası eklenebilir."
                    )
        if not docs:
            return 0

        ids = [self._document_id(doc) for doc in docs]
        with self._lock:
            # Stable IDs prevent the same source/chunk from inflating the collection.
            self.vectorstore.add_documents(docs, ids=ids)
            self._prune_if_needed()
        return len(docs)

    def add_code_file(self, file_path: str, content: str, repo: str = "unknown") -> int:
        return self.add_texts([content], metadatas=[{
            "source": file_path,
            "repo": repo,
            "type": "code",
        }])

    def _prune_if_needed(self) -> None:
        collection = getattr(self.vectorstore, "_collection", None)
        if collection is None:
            return
        count = collection.count()
        excess = count - self.max_documents
        if excess <= 0:
            return
        snapshot = collection.get(include=["metadatas"])
        ids = snapshot.get("ids", [])
        metadatas = snapshot.get("metadatas") or [{} for _ in ids]
        ordered = sorted(
            zip(ids, metadatas),
            key=lambda pair: str((pair[1] or {}).get("created_at", "")),
        )
        # Only remove the oldest completed knowledge chunks; never clear the collection.
        delete_ids = [doc_id for doc_id, _metadata in ordered[:excess]]
        if delete_ids:
            collection.delete(ids=delete_ids)
            logger.info("RAG sınırı için %s eski bilgi parçası temizlendi.", len(delete_ids))

    def search(self, query: str, k: int = 6) -> List[Document]:
        if not isinstance(query, str) or not query.strip():
            return []
        safe_k = max(1, min(int(k), 20))
        try:
            return self.vectorstore.similarity_search(query.strip()[:4000], k=safe_k, **({"filter": {"tenant_id": getattr(self, "tenant_id", None)}} if getattr(self, "tenant_id", None) else {}))
        except Exception as exc:
            # Retrieval failure must not take down the chat panel.
            logger.warning("Yerel RAG araması kullanılamıyor (%s).", type(exc).__name__)
            return []

    def search_with_score(self, query: str, k: int = 6):
        if not isinstance(query, str) or not query.strip():
            return []
        try:
            return self.vectorstore.similarity_search_with_score(query.strip()[:4000], k=max(1, min(int(k), 20)), **({"filter": {"tenant_id": self.tenant_id}} if self.tenant_id else {}))
        except Exception as exc:
            logger.warning("Yerel RAG puanlı araması kullanılamıyor (%s).", type(exc).__name__)
            return []

    def get_context(self, query: str, k: int = 6) -> str:
        docs = self.search(query, k=k)
        if not docs:
            return "İlgili yerel bilgi bulunamadı; bu bir hata değil, bellek henüz boş veya geçici olarak erişilemiyor."
        parts = []
        total = 0
        for i, doc in enumerate(docs, 1):
            source = str(doc.metadata.get("source", "bilinmeyen kaynak"))[:250]
            piece = f"[{i}] ({source})\n{doc.page_content}"
            if total + len(piece) > 12000:
                break
            parts.append(piece)
            total += len(piece)
        return "\n\n---\n\n".join(parts)

    def stats(self) -> dict:
        collection = getattr(self.vectorstore, "_collection", None)
        try:
            count = int(collection.count()) if collection is not None else 0
        except Exception:
            count = 0
        disk_bytes = 0
        try:
            disk_bytes = sum(p.stat().st_size for p in self.persist_directory.rglob("*") if p.is_file())
        except OSError:
            pass
        return {
            "mode": "local",
            "embedding_provider": getattr(self, "embedding_provider", "unknown"),
            "documents": count,
            "max_documents": self.max_documents,
            "max_chunks_per_ingest": self.max_chunks_per_ingest,
            "max_chars_per_ingest": self.max_chars_per_ingest,
            "disk_bytes": disk_bytes,
            "pruning": True,
        }
