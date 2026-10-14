"""
Curiosity Matrix — when idle, explore unknown topics and grow the knowledge base.
Not task-driven: philosophy, science, history, math, arts.
Never executes external actions beyond sanitized knowledge expansion.
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.knowledge_expander import KnowledgeExpander
from core.ollama_client import OllamaClient

logger = logging.getLogger("sentinel.curiosity")

CURIOSITY_POOL = [
    # Science & math
    "unsolved problems in mathematics explained simply",
    "information theory shannon entropy basics",
    "quantum computing practical limitations 2025 2026",
    "complexity theory P vs NP overview",
    "graph theory algorithms modern applications",
    # Biology / medicine (research only — not medical advice)
    "pubmed open access recent machine learning in biology",
    "systems biology network analysis methods",
    "epidemiology basic concepts correlation vs causation",
    "neuroscience memory formation summary",
    # Philosophy & history
    "philosophy of mind consciousness debates",
    "history of cryptography from cipher to modern",
    "ethics of autonomous systems overview",
    "scientific method history and limits",
    # Systems & space
    "distributed systems consensus algorithms raft paxos",
    "astronomy recent discoveries exoplanets",
    "climate data analysis methods not advocacy",
    "energy efficient computing hardware trends",
    # Culture & media literacy
    "media literacy detecting misinformation techniques",
    "history of open source software movement",
    "design patterns beyond gang of four",
]


class CuriosityEngine:
    def __init__(
        self,
        ollama: Optional[OllamaClient] = None,
        expander: Optional[KnowledgeExpander] = None,
        state_path: str = "./memory/curiosity_state.json",
    ):
        self.ollama = ollama or OllamaClient()
        self.expander = expander or KnowledgeExpander(ollama=self.ollama)
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"explored": [], "last_run": None, "notes": []}

    def _save(self) -> None:
        self.state_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def pick_topic(self) -> str:
        explored = set(self.state.get("explored", []))
        candidates = [t for t in CURIOSITY_POOL if t not in explored]
        if not candidates:
            candidates = CURIOSITY_POOL.copy()
            self.state["explored"] = []
        topic = random.choice(candidates)
        return topic

    def run_once(self) -> Dict[str, Any]:
        """One curiosity cycle: pick topic → expand knowledge → short reflection."""
        topic = self.pick_topic()
        logger.info(f"Curiosity exploring: {topic}")
        expand_result = self.expander.expand_once(extra_topics=[topic])

        reflection = ""
        try:
            ctx = self.expander.search_knowledge(topic, k=3)
            reflection = self.ollama.chat(
                f"Konu: {topic}\n\nBilgi özeti:\n{ctx[:3000]}\n\n"
                "Bu konudan 3 kısa merak noktası veya açık soru yaz. "
                "Tıbbi tavsiye veya eylem emri verme.",
                system="Meraklı araştırmacı. Sadece sorular ve gözlemler.",
            )
        except Exception as e:
            logger.warning(f"Curiosity reflection failed: {e}")
            reflection = "(reflection skipped)"

        self.state.setdefault("explored", []).append(topic)
        self.state["explored"] = self.state["explored"][-100:]
        self.state["last_run"] = datetime.utcnow().isoformat()
        self.state.setdefault("notes", []).append(
            {"topic": topic, "at": self.state["last_run"], "pages": expand_result.get("pages_ingested", 0)}
        )
        self.state["notes"] = self.state["notes"][-50:]
        self._save()

        return {
            "topic": topic,
            "expand": expand_result,
            "reflection": reflection[:2000],
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "last_run": self.state.get("last_run"),
            "explored_count": len(self.state.get("explored", [])),
            "recent": self.state.get("notes", [])[-5:],
        }
