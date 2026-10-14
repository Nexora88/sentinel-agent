"""
RAG (Retrieval Augmented Generation) memory system.
Continuously learns from code, docs and past reviews.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.ollama_client import OllamaClient


class MemoryStore:
    """Persistent vector memory for Sentinel."""

    def __init__(
        self,
        collection_name: str = "sentinel_memory",
        persist_directory: str = "./memory",
        ollama: Optional[OllamaClient] = None,
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.ollama = ollama or OllamaClient()
        self.collection_name = collection_name

        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.ollama.embeddings,
            persist_directory=str(self.persist_directory),
        )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n\n", "\n", " ", ""],
        )

    def add_texts(self, texts: List[str], metadatas: Optional[List[dict]] = None) -> None:
        """Add raw texts to memory."""
        docs = self.splitter.create_documents(texts, metadatas=metadatas)
        self.vectorstore.add_documents(docs)

    def add_code_file(self, file_path: str, content: str, repo: str = "unknown") -> None:
        """Add a single code file into memory."""
        metadata = {
            "source": file_path,
            "repo": repo,
            "type": "code",
        }
        self.add_texts([content], metadatas=[metadata])

    def search(self, query: str, k: int = 6) -> List[Document]:
        """Retrieve relevant memories."""
        return self.vectorstore.similarity_search(query, k=k)

    def search_with_score(self, query: str, k: int = 6):
        return self.vectorstore.similarity_search_with_score(query, k=k)

    def get_context(self, query: str, k: int = 6) -> str:
        """Return concatenated context string for prompts."""
        docs = self.search(query, k=k)
        if not docs:
            return "No relevant memory found."

        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "unknown")
            parts.append(f"[{i}] ({source})\n{doc.page_content}")

        return "\n\n---\n\n".join(parts)
