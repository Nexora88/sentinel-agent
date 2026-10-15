"""
Model Router — hızlı sohbet vs derin analiz.
Hepsi Ollama; ücretli API yok.
"""

from __future__ import annotations

import os
from typing import Optional

from core.ollama_client import OllamaClient


class ModelRouter:
    def __init__(self):
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        default = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
        fast = os.getenv("OLLAMA_MODEL_FAST", default)
        deep = os.getenv("OLLAMA_MODEL_DEEP", default)
        embed = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

        self.fast = OllamaClient(model=fast, embed_model=embed, base_url=base, temperature=0.3)
        self.deep = OllamaClient(model=deep, embed_model=embed, base_url=base, temperature=0.15)
        self.default = OllamaClient(model=default, embed_model=embed, base_url=base)

    def for_task(self, task: str = "chat") -> OllamaClient:
        task = (task or "chat").lower()
        if task in {"chat", "status", "route", "plan_light"}:
            return self.fast
        if task in {"code", "review", "security", "night", "podcast", "plan"}:
            return self.deep
        return self.default

    def info(self) -> dict:
        return {
            "fast": self.fast.model_name,
            "deep": self.deep.model_name,
            "default": self.default.model_name,
            "embed": self.default.embed_model_name,
        }
