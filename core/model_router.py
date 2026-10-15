"""
Model Router — görev türüne ve yerel donanım profiline göre başlangıç modeli seçer.
Model önerileri garanti değildir; açık OLLAMA_MODEL* ayarları otomatik seçimin önüne geçer.
"""
from __future__ import annotations
import os
from core.ollama_client import OllamaClient
from core.runtime_profile import get_runtime_profile


def _model_defaults() -> tuple[str, str, str, str]:
    """Return default, fast, deep and embedding models without network probing."""
    embed = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    profile_enabled = os.getenv("MKAOS_AUTO_MODEL_PROFILE", "true").strip().lower() not in {"0", "false", "no", "off"}
    profile = get_runtime_profile() if profile_enabled else {"model_guidance": {}}
    guidance = profile.get("model_guidance", {})
    safe_fallback = os.getenv("MKAOS_MINIMAL_MODEL", "qwen2.5:0.5b")
    suggested_chat = guidance.get("suggested_chat_model") or safe_fallback
    suggested_code = guidance.get("suggested_code_model") or suggested_chat
    default = os.getenv("OLLAMA_MODEL", suggested_chat)
    fast = os.getenv("OLLAMA_MODEL_FAST", suggested_chat)
    deep = os.getenv("OLLAMA_MODEL_DEEP", suggested_code)
    return default, fast, deep, embed


class ModelRouter:
    def __init__(self):
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        default, fast, deep, embed = _model_defaults()
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
        profile = get_runtime_profile()
        return {
            "fast": self.fast.model_name,
            "deep": self.deep.model_name,
            "default": self.default.model_name,
            "embed": self.default.embed_model_name,
            "runtime_profile": profile,
            "automatic_profile_enabled": os.getenv("MKAOS_AUTO_MODEL_PROFILE", "true").strip().lower() not in {"0", "false", "no", "off"},
        }
