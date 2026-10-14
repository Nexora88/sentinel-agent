"""
Local Document Ingester
Upload PDF / Markdown / TXT into the knowledge universe (RAG).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from core.ollama_client import OllamaClient
from core.rag import MemoryStore
from core.safety import sanitize_web_content

logger = logging.getLogger("sentinel.doc_ingester")


class DocumentIngester:
    def __init__(self, ollama: Optional[OllamaClient] = None, memory: Optional[MemoryStore] = None):
        self.ollama = ollama or OllamaClient()
        self.memory = memory or MemoryStore(
            collection_name="universe_knowledge",
            persist_directory="./memory/universe_kb",
            ollama=self.ollama,
        )

    def _extract_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".md", ".txt", ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".toml", ".csv"}:
            return path.read_text(encoding="utf-8", errors="ignore")

        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(path))
                parts = []
                for page in reader.pages[:50]:  # safety limit
                    t = page.extract_text() or ""
                    parts.append(t)
                return "\n".join(parts)
            except ImportError:
                logger.warning("pypdf not installed — cannot read PDF")
                return ""
            except Exception as e:
                logger.error(f"PDF extract failed: {e}")
                return ""

        return ""

    def ingest_file(self, file_path: str, source_label: Optional[str] = None) -> dict:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return {"success": False, "error": f"Dosya bulunamadı: {file_path}"}

        text = self._extract_text(path)
        if not text or len(text.strip()) < 50:
            return {"success": False, "error": "İçerik çıkarılamadı veya çok kısa"}

        text = sanitize_web_content(text)
        label = source_label or path.name

        self.memory.add_texts(
            [text],
            metadatas=[{
                "source": label,
                "type": "local_document",
                "path": str(path),
            }],
        )
        logger.info(f"Ingested local document: {label} ({len(text)} chars)")
        return {
            "success": True,
            "source": label,
            "chars": len(text),
            "message": f"✅ '{label}' bilgi evrenine eklendi ({len(text)} karakter)",
        }

    def ingest_directory(self, dir_path: str, extensions: Optional[List[str]] = None) -> dict:
        extensions = extensions or [".md", ".txt", ".pdf"]
        root = Path(dir_path)
        if not root.is_dir():
            return {"success": False, "error": "Klasör bulunamadı"}

        results = []
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in extensions:
                r = self.ingest_file(str(p))
                results.append(r)

        ok = sum(1 for r in results if r.get("success"))
        return {
            "success": True,
            "ingested": ok,
            "total_seen": len(results),
            "message": f"{ok}/{len(results)} belge eklendi",
        }
