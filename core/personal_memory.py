"""
Personal Memory — Sentinel gets to know YOU.
Stores user profile, preferences, conversation history and learned facts.
Everything stays local (ChromaDB).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.ollama_client import OllamaClient

logger = logging.getLogger("sentinel.personal_memory")


class PersonalMemory:
    """Long-term memory about the human owner."""

    def __init__(
        self,
        persist_directory: str = "./memory/personal",
        ollama: Optional[OllamaClient] = None,
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.profile_path = self.persist_directory / "profile.json"

        self.ollama = ollama or OllamaClient()

        self.vectorstore = Chroma(
            collection_name="personal_memory",
            embedding_function=self.ollama.embeddings,
            persist_directory=str(self.persist_directory / "chroma"),
        )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
        )

        self._profile: Dict[str, Any] = self._load_profile()

    def _load_profile(self) -> Dict[str, Any]:
        if self.profile_path.exists():
            try:
                data = json.loads(self.profile_path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("profile must be a JSON object")
                return data
            except Exception as exc:
                raise RuntimeError(
                    f"Local profile is unreadable; preserve and recover {self.profile_path} before restarting."
                ) from exc
        now = datetime.utcnow().isoformat()
        return {
            "name": None,
            "preferred_language": "tr",
            "coding_style": None,
            "projects": [],
            "preferences": {},
            "facts": [],
            "created_at": now,
            "updated_at": now,
        }

    def _save_profile(self) -> None:
        self._profile["updated_at"] = datetime.utcnow().isoformat()
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=str(self.profile_path.parent),
                prefix=".profile-", suffix=".tmp", delete=False
            ) as temp:
                json.dump(self._profile, temp, ensure_ascii=False, indent=2)
                temp.flush()
                os.fsync(temp.fileno())
                temp_name = temp.name
            try:
                os.chmod(temp_name, 0o600)
            except OSError:
                pass
            os.replace(temp_name, self.profile_path)
            try:
                os.chmod(self.profile_path, 0o600)
            except OSError:
                pass
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)

    @property
    def profile(self) -> Dict[str, Any]:
        return self._profile

    def set_name(self, name: str) -> None:
        self._profile["name"] = name
        self._save_profile()
        self.add_fact(f"Kullanıcının adı: {name}")

    def add_fact(self, fact: str, category: str = "general") -> None:
        """Store a lasting fact about the user."""
        fact = fact.strip()
        if not fact:
            return
        if fact not in self._profile["facts"]:
            self._profile["facts"].append(fact)
            self._save_profile()

        self.vectorstore.add_documents(
            [
                Document(
                    page_content=fact,
                    metadata={
                        "type": "fact",
                        "category": category,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
            ]
        )
        logger.info(f"Learned fact: {fact[:80]}...")

    def add_preference(self, key: str, value: str) -> None:
        self._profile["preferences"][key] = value
        self._save_profile()
        self.add_fact(f"Tercih: {key} = {value}", category="preference")

    def add_project(self, project: str) -> None:
        if project not in self._profile["projects"]:
            self._profile["projects"].append(project)
            self._save_profile()
            self.add_fact(f"Proje: {project}", category="project")

    def remember_conversation(self, role: str, content: str) -> None:
        """Store a conversation turn."""
        self.vectorstore.add_documents(
            [
                Document(
                    page_content=f"{role}: {content}",
                    metadata={
                        "type": "conversation",
                        "role": role,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
            ]
        )

    def search(self, query: str, k: int = 8) -> List[Document]:
        return self.vectorstore.similarity_search(query, k=k)

    def get_context_for_prompt(self, query: str = "", k: int = 6) -> str:
        """Build a rich context string about the user for the LLM."""
        parts = []

        # Profile summary
        name = self._profile.get("name") or "Kullanıcı"
        parts.append(f"### Kullanıcı Profili\nAd: {name}")
        if self._profile.get("preferred_language"):
            parts.append(f"Dil: {self._profile['preferred_language']}")
        if self._profile.get("coding_style"):
            parts.append(f"Kod stili: {self._profile['coding_style']}")
        if self._profile.get("projects"):
            parts.append("Projeler: " + ", ".join(self._profile["projects"][-5:]))
        if self._profile.get("preferences"):
            prefs = ", ".join(f"{k}={v}" for k, v in list(self._profile["preferences"].items())[-5:])
            parts.append(f"Tercihler: {prefs}")

        # Recent facts
        if self._profile.get("facts"):
            recent_facts = self._profile["facts"][-8:]
            parts.append("### Bilinen Gerçekler\n" + "\n".join(f"- {f}" for f in recent_facts))

        # Vector search
        if query:
            docs = self.search(query, k=k)
            if docs:
                conv_parts = []
                for d in docs:
                    if d.metadata.get("type") == "conversation":
                        conv_parts.append(d.page_content)
                    else:
                        conv_parts.append(f"[Hafıza] {d.page_content}")
                if conv_parts:
                    parts.append("### İlgili Hafıza\n" + "\n".join(conv_parts[:6]))

        return "\n\n".join(parts) if parts else "Henüz kullanıcı hakkında bilgi yok."

    def extract_and_learn(self, user_message: str, assistant_reply: str) -> None:
        """Simple heuristic: extract facts from conversation (can be improved later with LLM)."""
        # Store the conversation turn
        self.remember_conversation("user", user_message)
        self.remember_conversation("assistant", assistant_reply)

        # Very light fact extraction (keywords)
        lower = user_message.lower()
        if any(w in lower for w in ["adım", "ismim", "benim adım", "bana "]):
            # Let the LLM decide later; for now just store raw
            pass

    def forget_matching(self, phrase: str, last_hours: int = 24) -> dict:
        """Delete exact-topic matches from personal vector memory and profile facts."""
        import time
        phrase = str(phrase or "").strip().casefold()
        if len(phrase) < 3:
            raise ValueError("Silme konusu en az 3 karakter olmalı.")
        hours = max(1, min(int(last_hours), 8760))
        cutoff = time.time() - hours * 3600
        collection = getattr(self.vectorstore, "_collection", None)
        deleted_vectors = 0
        if collection is not None:
            snapshot = collection.get(include=["documents", "metadatas"])
            ids = snapshot.get("ids", [])
            docs = snapshot.get("documents") or ["" for _ in ids]
            metas = snapshot.get("metadatas") or [{} for _ in ids]
            remove = []
            for item_id, body, metadata in zip(ids, docs, metas):
                metadata = metadata or {}
                stamp = metadata.get("timestamp") or metadata.get("created_at")
                try:
                    from datetime import datetime, timezone
                    parsed = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    recent = parsed.timestamp() >= cutoff
                except (TypeError, ValueError, OverflowError):
                    recent = False
                if recent and phrase in str(body or "").casefold():
                    remove.append(item_id)
            if remove:
                collection.delete(ids=remove)
                deleted_vectors = len(remove)
        # Profile facts have no per-fact timestamp in the existing schema. Preserve them
        # during bounded-window deletion because their age cannot be established.
        deleted_facts = 0
        preserved_facts = sum(1 for fact in self._profile.get("facts", []) if phrase in str(fact).casefold())
        return {"deleted_vector_records": deleted_vectors, "deleted_profile_facts": deleted_facts,
                "unscoped_profile_facts_preserved": preserved_facts,
                "scope": "timestamped personal vector records; exact phrase match; requested time window",
                "limitations": ["Zaman damgası olmayan profil gerçekleri korunur; ayrıca incelenmelidir.",
                                "Bu işlem yedekleri, dışa aktarımları, sistem günlüklerini veya model ağırlıklarını temizlemez.",
                                "Bu bir adli veri imha/SSD secure erase garantisi değildir."]}
