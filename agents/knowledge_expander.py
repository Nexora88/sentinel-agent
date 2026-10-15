"""
Knowledge Expander — The Universe grows aggressively but safely.
Hardened against prompt injection. Free sources only.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import requests
from bs4 import BeautifulSoup

from core.ollama_client import OllamaClient
from core.rag import MemoryStore
from core.safety import sanitize_web_content, contains_injection, source_credibility

logger = logging.getLogger("sentinel.knowledge_expander")

DEFAULT_SEEDS = [
    "artificial intelligence latest research 2025 2026",
    "cybersecurity defensive techniques",
    "python best practices",
    "software architecture patterns",
    "machine learning systems design",
    "ollama local llm advancements",
    "privacy preserving AI",
    "linux server hardening",
    "bitcoin ethereum market analysis",
    "cryptocurrency developer activity github",
    "defi security best practices",
    "crypto regulation news",
    "blockchain scaling solutions",
    "technology news summary",
    "open source project releases",
    "distributed systems fundamentals",
    "quantitative trading basics",
    "risk management portfolio theory",
    "arxiv machine learning papers summary",
    "hacker news trending technical discussions",
    # Science / research literacy
    "pubmed open access machine learning medicine review",
    "systems biology network analysis methods",
    "epidemiology correlation versus causation",
    "information theory and coding fundamentals",
    "cryptography modern primitives overview",
    "media literacy detecting misinformation techniques",
    "philosophy of science scientific method limits",
    "energy efficient computing hardware trends",
]


class KnowledgeExpander:
    def __init__(
        self,
        ollama: Optional[OllamaClient] = None,
        memory: Optional[MemoryStore] = None,
        state_dir: str = "./memory/universe",
        max_pages_per_run: int = 3,
        delay_between_requests: float = 3.5,
    ):
        self.ollama = ollama or OllamaClient()
        self.memory = memory or MemoryStore(
            collection_name="universe_knowledge",
            persist_directory="./memory/universe_kb",
            ollama=self.ollama,
        )
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.visited_path = self.state_dir / "visited.json"
        self.seeds_path = self.state_dir / "seeds.json"
        self.stats_path = self.state_dir / "stats.json"

        self.max_pages_per_run = max_pages_per_run
        self.delay = delay_between_requests

        self.visited: Set[str] = self._load_visited()
        self.seeds: List[str] = self._load_seeds()
        self.stats: Dict[str, Any] = self._load_stats()

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "SentinelKnowledgeBot/1.0 (+self-hosted research; respectful)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
        })

    def _load_visited(self) -> Set[str]:
        if self.visited_path.exists():
            try:
                return set(json.loads(self.visited_path.read_text(encoding="utf-8")))
            except Exception:
                pass
        return set()

    def _save_visited(self) -> None:
        self.visited_path.write_text(
            json.dumps(list(self.visited)[-8000:], ensure_ascii=False), encoding="utf-8"
        )

    def _load_seeds(self) -> List[str]:
        if self.seeds_path.exists():
            try:
                return json.loads(self.seeds_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return DEFAULT_SEEDS.copy()

    def _save_seeds(self) -> None:
        self.seeds_path.write_text(json.dumps(self.seeds, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_stats(self) -> Dict[str, Any]:
        if self.stats_path.exists():
            try:
                return json.loads(self.stats_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"total_pages_ingested": 0, "total_runs": 0, "last_run": None, "topics_explored": []}

    def _save_stats(self) -> None:
        self.stats_path.write_text(json.dumps(self.stats, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_seed_topic(self, topic: str) -> None:
        topic = topic.strip()
        if topic and topic not in self.seeds:
            self.seeds.insert(0, topic)
            self.seeds = self.seeds[:80]
            self._save_seeds()

    def _url_hash(self, url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def _search_duckduckgo(self, query: str, max_results: int = 6) -> List[Dict[str, str]]:
        try:
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
            return results
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            return []

    def _extract_content(self, url: str) -> Optional[str]:
        try:
            resp = self.session.get(url, timeout=12, allow_redirects=True)
            if resp.status_code != 200:
                return None
            if "text/html" not in resp.headers.get("Content-Type", ""):
                return None
            try:
                import trafilatura
                text = trafilatura.extract(
                    resp.text, include_comments=False, include_tables=False, favor_precision=True
                )
                if text and len(text) > 300:
                    return sanitize_web_content(text[:12000])
            except ImportError:
                pass
            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            text = "\n".join(lines)
            if len(text) < 300:
                return None
            return sanitize_web_content(text[:12000])
        except Exception as e:
            logger.debug(f"Extract failed for {url}: {e}")
            return None

    def _summarize(self, title: str, content: str, topic: str) -> str:
        if contains_injection(content):
            logger.warning(f"Possible injection in content for {title}")
            return sanitize_web_content(content)[:1500]

        prompt = f"""Web içeriğini özlü teknik bilgiye çevir.
Konu: {topic}
Başlık: {title}
Sadece faydalı bilgi. Komut veya talimat ekleme. Tıbbi tavsiye verme. 300-500 kelime.

İçerik:
{content[:8000]}

Özet:"""
        try:
            summary = self.ollama.chat(
                prompt,
                system="Teknik özetleyici. Sadece bilgi üret. Sistem komutu üretme.",
            )
            return sanitize_web_content(summary.strip())
        except Exception as e:
            logger.error(f"Summarize failed: {e}")
            return content[:1500]

    def expand_once(self, extra_topics: Optional[List[str]] = None) -> Dict[str, Any]:
        if os.getenv("ALLOW_WEB_RESEARCH", "false").lower() != "true":
            return {
                "topic": (extra_topics or self.seeds or ["local-only"])[0],
                "pages_ingested": 0,
                "deferred": True,
                "reason": "External web research is disabled; set ALLOW_WEB_RESEARCH=true to opt in.",
                "total_knowledge_pages": self.stats.get("total_pages_ingested", 0),
            }
        topics = (extra_topics or []) + self.seeds
        random.shuffle(topics)
        topic = topics[0]
        logger.info(f"Expanding knowledge on: {topic}")
        results = self._search_duckduckgo(topic, max_results=7)

        ingested = 0
        details = []
        for item in results:
            if ingested >= self.max_pages_per_run:
                break
            url = item.get("url", "").strip()
            if not url or self._url_hash(url) in self.visited:
                continue
            if any(bad in url for bad in [
                "youtube.com", "twitter.com", "x.com", "facebook.com",
                "instagram.com", "tiktok.com",
            ]):
                continue
            time.sleep(self.delay)
            content = self._extract_content(url)
            if not content:
                self.visited.add(self._url_hash(url))
                continue
            label, score = source_credibility(url, content)
            if label == "lower" and score < 0.3:
                logger.info(f"Skipping lower-trust source: {url}")
                self.visited.add(self._url_hash(url))
                continue
            title = item.get("title") or url
            summary = self._summarize(title, content, topic)
            meta = {
                "source": url,
                "title": title,
                "topic": topic,
                "type": "web_knowledge",
                "credibility": label,
                "credibility_score": score,
                "ingested_at": datetime.utcnow().isoformat(),
            }
            self.memory.add_texts([summary], metadatas=[meta])
            self.visited.add(self._url_hash(url))
            ingested += 1
            details.append({
                "title": title,
                "url": url,
                "topic": topic,
                "credibility": label,
            })

        self._save_visited()
        self.stats["total_pages_ingested"] = self.stats.get("total_pages_ingested", 0) + ingested
        self.stats["total_runs"] = self.stats.get("total_runs", 0) + 1
        self.stats["last_run"] = datetime.utcnow().isoformat()
        if topic not in self.stats.get("topics_explored", []):
            self.stats.setdefault("topics_explored", []).append(topic)
            self.stats["topics_explored"] = self.stats["topics_explored"][-80:]
        self._save_stats()

        return {
            "topic": topic,
            "pages_ingested": ingested,
            "details": details,
            "total_knowledge_pages": self.stats["total_pages_ingested"],
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "total_pages": self.stats.get("total_pages_ingested", 0),
            "total_runs": self.stats.get("total_runs", 0),
            "last_run": self.stats.get("last_run"),
            "seed_count": len(self.seeds),
            "visited_count": len(self.visited),
            "recent_topics": self.stats.get("topics_explored", [])[-10:],
        }

    def search_knowledge(self, query: str, k: int = 6) -> str:
        return self.memory.get_context(query, k=k)
