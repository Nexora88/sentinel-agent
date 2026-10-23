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
        require_semantic = os.getenv("SEKA_REQUIRE_SEMANTIC_EMBEDDINGS", "false").strip().lower() in {"1", "true", "yes", "on"}
        requested_provider = os.getenv("SEKA_EMBEDDINGS_PROVIDER", "").strip().lower()
        requested_storage_backend = os.getenv("SEKA_RAG_STORAGE_BACKEND", "chroma").strip().lower()
        if requested_storage_backend not in {"chroma", "crypto-sqlite"}:
            raise ValueError("SEKA_RAG_STORAGE_BACKEND must be chroma or crypto-sqlite.")
        if requested_storage_backend == "crypto-sqlite" and requested_provider == "ollama":
            raise ValueError("Crypto-RAG requires local mkaos-native or local-semantic embeddings; Ollama mode is not initialized.")
        local_model_path = os.getenv("SEKA_LOCAL_EMBEDDING_MODEL_PATH", "").strip()
        if require_semantic and requested_provider not in {"", "local-semantic"}:
            raise ValueError("SEKA_REQUIRE_SEMANTIC_EMBEDDINGS is enabled; only local-semantic retrieval is permitted.")
        if require_semantic:
            self.embedding_provider = "local-semantic"
        elif requested_provider:
            self.embedding_provider = requested_provider
        elif local_model_path and Path(local_model_path).expanduser().is_dir():
            self.embedding_provider = "local-semantic"
        else:
            self.embedding_provider = "mkaos-native"
        self.semantic_retrieval_required = require_semantic
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
        self.embedding_function = embedding_function
        self.storage_backend = requested_storage_backend
        if self.storage_backend == "crypto-sqlite":
            if self.embedding_provider == "ollama":
                raise ValueError("Crypto-RAG currently requires a local embedding object; choose mkaos-native or local-semantic.")
            raw_crypto_path = os.getenv("SEKA_CRYPTO_RAG_PATH", "").strip()
            if not raw_crypto_path:
                raise ValueError("SEKA_CRYPTO_RAG_PATH is required for crypto-sqlite; use a new path outside the Chroma directory.")
            crypto_path = Path(raw_crypto_path).expanduser()
            source_root = self.persist_directory.resolve()
            target_path = crypto_path.resolve()
            if target_path == source_root or source_root in target_path.parents:
                raise ValueError("Crypto-RAG database must be outside the plaintext Chroma directory.")
            from core.crypto_rag import EncryptedVectorStore, key_from_env
            self.crypto_store = EncryptedVectorStore(crypto_path, key_from_env())
            self.vectorstore = None
        else:
            self.crypto_store = None
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
            if getattr(self, "crypto_store", None) is not None:
                vectors = self.embedding_function.embed_documents([doc.page_content for doc in docs])
                if len(vectors) != len(docs):
                    raise ValueError("Embedding provider returned a mismatched vector count.")
                self.crypto_store.upsert_many([
                    {
                        "record_id": doc_id,
                        "embedding": vector,
                        "document": doc.page_content,
                        "metadata": doc.metadata,
                    }
                    for doc_id, doc, vector in zip(ids, docs, vectors)
                ])
            else:
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
        if getattr(self, "crypto_store", None) is not None:
            count = self.crypto_store.count()
            excess = count - self.max_documents
            if excess <= 0:
                return
            records = self.crypto_store.list_records()
            ordered = sorted(
                records,
                key=lambda row: str(row["metadata"].get("created_at", "")),
            )
            delete_ids = [row["id"] for row in ordered[:excess]]
            for record_id in delete_ids:
                self.crypto_store.delete(record_id)
            if delete_ids:
                logger.info("Encrypted RAG limit pruned %s oldest records.", len(delete_ids))
            return
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

    def _search_filter(self) -> dict:
        # The same tenant constraint is applied before reranking; reranking cannot
        # introduce documents outside the caller's authorized candidate set.
        return {"filter": {"tenant_id": self.tenant_id}} if self.tenant_id else {}

    @staticmethod
    def _hybrid_enabled() -> bool:
        return os.getenv("SEKA_RAG_HYBRID_RERANK", "true").strip().lower() not in {
            "0", "false", "no", "off"
        }

    def _rerank(self, query: str, documents: list[Document], limit: int) -> list[Document]:
        if not self._hybrid_enabled() or len(documents) < 2:
            return documents[:limit]
        from core.hybrid_rag import hybrid_rerank
        return hybrid_rerank(query, documents, limit=limit)

    def search(self, query: str, k: int = 6) -> List[Document]:
        if not isinstance(query, str) or not query.strip():
            return []
        safe_k = max(1, min(int(k), 20))
        candidate_k = min(100, max(safe_k, safe_k * 4))
        try:
            bounded_query = query.strip()[:4000]
            if getattr(self, "crypto_store", None) is not None:
                rows = self.crypto_store.search(
                    self.embedding_function.embed_query(bounded_query),
                    limit=candidate_k,
                    metadata_filter={"tenant_id": self.tenant_id} if self.tenant_id else None,
                )
                candidates = [Document(page_content=row["document"], metadata=row["metadata"]) for row in rows]
            else:
                candidates = self.vectorstore.similarity_search(
                    bounded_query, k=candidate_k, **self._search_filter()
                )
            return self._rerank(bounded_query, candidates, safe_k)
        except Exception as exc:
            logger.warning("Yerel RAG araması kullanılamıyor (%s).", type(exc).__name__)
            return []

    def search_with_score(self, query: str, k: int = 6):
        if not isinstance(query, str) or not query.strip():
            return []
        safe_k = max(1, min(int(k), 20))
        candidate_k = min(100, max(safe_k, safe_k * 4))
        try:
            bounded_query = query.strip()[:4000]
            if getattr(self, "crypto_store", None) is not None:
                rows = self.crypto_store.search(
                    self.embedding_function.embed_query(bounded_query),
                    limit=candidate_k,
                    metadata_filter={"tenant_id": self.tenant_id} if self.tenant_id else None,
                )
                pairs = [(Document(page_content=row["document"], metadata=row["metadata"]), row["score"]) for row in rows]
            else:
                pairs = self.vectorstore.similarity_search_with_score(
                    bounded_query, k=candidate_k, **self._search_filter()
                )
            ranked_docs = self._rerank(bounded_query, [doc for doc, _ in pairs], safe_k)
            score_by_identity = {id(doc): score for doc, score in pairs}
            return [(doc, score_by_identity[id(doc)]) for doc in ranked_docs]
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
            count = self.crypto_store.count() if getattr(self, "crypto_store", None) is not None else (int(collection.count()) if collection is not None else 0)
        except Exception:
            count = 0
        disk_bytes = 0
        try:
            disk_paths = {p for p in self.persist_directory.rglob("*") if p.is_file()}
            if getattr(self, "crypto_store", None) is not None:
                disk_paths.update(p for p in (
                    self.crypto_store.path,
                    Path(str(self.crypto_store.path) + "-wal"),
                    Path(str(self.crypto_store.path) + "-shm"),
                ) if p.is_file())
            disk_bytes = sum(p.stat().st_size for p in disk_paths)
        except OSError:
            pass
        return {
            "mode": "local",
            "storage_backend": self.storage_backend,
            "embedding_provider": getattr(self, "embedding_provider", "unknown"),
            "semantic_retrieval_required": getattr(self, "semantic_retrieval_required", False),
            "documents": count,
            "max_documents": self.max_documents,
            "max_chunks_per_ingest": self.max_chunks_per_ingest,
            "max_chars_per_ingest": self.max_chars_per_ingest,
            "disk_bytes": disk_bytes,
            "pruning": True,
        }
