"""
Configuration loader for Sentinel Agent.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv

load_dotenv()

# Keep optional telemetry/tracing disabled even when no .env file is present.
for _key, _value in {
    "ANONYMIZED_TELEMETRY": "False",
    "CHROMA_TELEMETRY": "False",
    "LANGCHAIN_TRACING_V2": "false",
    "LANGSMITH_TRACING": "false",
    "OTEL_SDK_DISABLED": "true",
}.items():
    os.environ.setdefault(_key, _value)

ROOT = Path(__file__).resolve().parent.parent


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class Settings:
    def __init__(self):
        self.settings = load_yaml(ROOT / "config" / "settings.yaml")
        self.agents_config = load_yaml(ROOT / "config" / "agents.yaml")
        self.permissions = load_yaml(ROOT / "config" / "permissions.yaml")

    @property
    def model_name(self) -> str:
        return os.getenv("OLLAMA_MODEL") or self.settings.get("model", {}).get("name", "qwen2.5-coder:32b")

    @property
    def ollama_base_url(self) -> str:
        return os.getenv("OLLAMA_BASE_URL") or self.settings.get("model", {}).get("base_url", "http://localhost:11434")

    @property
    def temperature(self) -> float:
        return float(self.settings.get("model", {}).get("temperature", 0.2))

    @property
    def require_approval(self) -> bool:
        return self.permissions.get("default", {}).get("require_approval", True)

    @property
    def watch_repos(self) -> List[str]:
        env_repos = os.getenv("WATCH_REPOS", "")
        if env_repos:
            return [r.strip() for r in env_repos.split(",") if r.strip()]
        return self.settings.get("watch", {}).get("repositories", [])

    @property
    def schedule_code_review(self) -> str:
        return self.settings.get("schedule", {}).get("code_review", "0 3 * * *")

    @property
    def schedule_security(self) -> str:
        return self.settings.get("schedule", {}).get("security_scan", "0 4 * * *")


settings = Settings()
