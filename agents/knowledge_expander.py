"""
Knowledge Expander — The Universe grows aggressively but safely.
Hardened against prompt injection. Free sources only.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import random
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from typing import Any, Dict, List, Optional, Set

import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup

from core.ollama_client import OllamaClient
from core.rag import MemoryStore
from core.safety import sanitize_web_content, contains_injection, source_credibility
from tools.website_scanner import UnsafeTarget, validate_public_url

logger = logging.getLogger("sentinel.knowledge_expander")


def _atomic_write_json(path: Path, data: Any) -> None:
    """Durably replace a local JSON state file without leaving partial writes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=str(path.parent),
            prefix=f".{path.name}-", suffix=".tmp", delete=False
        ) as temp:
            json.dump(data, temp, ensure_ascii=False, indent=2)
            temp.flush()
            os.fsync(temp.fileno())
            temp_name = temp.name
        try:
            os.chmod(temp_name, 0o600)
        except OSError:
            pass
        os.replace(temp_name, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)

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
        self.session.trust_env = False

    def _load_visited(self) -> Set[str]:
        if not self.visited_path.exists():
            return set()
        try:
            data = json.loads(self.visited_path.read_text(encoding="utf-8"))
            if not isinstance(data, list) or any(not isinstance(item, str) for item in data):
                raise ValueError("visited state must be a list of URLs")
            return set(data)
        except Exception as exc:
            raise RuntimeError(
                f"Visited URL state is unreadable; preserve and recover {self.visited_path}."
            ) from exc

    def _save_visited(self) -> None:
        _atomic_write_json(self.visited_path, list(self.visited)[-8000:])

    def _load_seeds(self) -> List[str]:
        if not self.seeds_path.exists():
            return DEFAULT_SEEDS.copy()
        try:
            data = json.loads(self.seeds_path.read_text(encoding="utf-8"))
            if not isinstance(data, list) or any(not isinstance(item, str) for item in data):
                raise ValueError("seed state must be a list of strings")
            return data
        except Exception as exc:
            raise RuntimeError(
                f"Research seed state is unreadable; preserve and recover {self.seeds_path}."
            ) from exc

    def _save_seeds(self) -> None:
        _atomic_write_json(self.seeds_path, self.seeds)

    def _load_stats(self) -> Dict[str, Any]:
        if not self.stats_path.exists():
            return {"total_pages_ingested": 0, "total_runs": 0, "last_run": None, "topics_explored": []}
        try:
            data = json.loads(self.stats_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("research stats must be a JSON object")
            return data
        except Exception as exc:
            raise RuntimeError(
                f"Research statistics are unreadable; preserve and recover {self.stats_path}."
            ) from exc

    def _save_stats(self) -> None:
        _atomic_write_json(self.stats_path, self.stats)

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
        """Fetch bounded HTML from public hosts; validate every redirect to reduce SSRF."""
        current = url
        response = None
        try:
            for _ in range(4):
                validate_public_url(current)
                response = self.session.get(
                    current, timeout=12, allow_redirects=False, stream=True
                )
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("Location")
                    response.close()
                    response = None
                    if not location:
                        return None
                    current = urljoin(current, location)
                    continue
                if response.status_code != 200:
                    return None
                if "text/html" not in response.headers.get("Content-Type", ""):
                    return None
                declared_size = response.headers.get("Content-Length")
                if declared_size and int(declared_size) > 2 * 1024 * 1024:
                    return None
                chunks = []
                total = 0
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > 2 * 1024 * 1024:
                        return None
                    chunks.append(chunk)
                html = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
                try:
                    import trafilatura
                    text = trafilatura.extract(
                        html, include_comments=False, include_tables=False, favor_precision=True
                    )
                    if text and len(text) > 300:
                        return sanitize_web_content(text[:12000])
                except ImportError:
                    pass
                soup = BeautifulSoup(html, "lxml")
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    tag.decompose()
                text = soup.get_text(separator="\n", strip=True)
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                text = "\n".join(lines)
                if len(text) < 300:
                    return None
                return sanitize_web_content(text[:12000])
            return None
        except (RequestException, UnsafeTarget, ValueError) as exc:
            logger.debug("Safe page extraction stopped (%s)", type(exc).__name__)
            return None
        finally:
            if response is not None:
                response.close()

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
