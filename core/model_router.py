"""Route all inference tasks to the resident MKAOS engine."""
from __future__ import annotations
from core.ollama_client import OllamaClient
from core.runtime_profile import get_runtime_profile

class ModelRouter:
    """Task profiles tune sampling, never switch to a different runtime or model."""
    def __init__(self):
        self.fast = OllamaClient(temperature=0.3)
        self.deep = OllamaClient(temperature=0.15)
        self.default = OllamaClient(temperature=0.2)

    def for_task(self, task: str = "chat") -> OllamaClient:
        task = (task or "chat").lower()
        if task in {"chat", "status", "route", "plan_light"}:
            return self.fast
        if task in {"code", "review", "security", "night", "podcast", "plan"}:
            return self.deep
        return self.default

    def info(self) -> dict:
        profile = get_runtime_profile()
        return {
            "engine": "MKAOS Rust resident server",
            "chat_provider": "mkaos",
            "fast": self.fast.model_name,
            "deep": self.deep.model_name,
            "default": self.default.model_name,
            "embedding_provider": "temporary local Ollama",
            "runtime_profile": profile,
            "automatic_profile_enabled": False,
        }
