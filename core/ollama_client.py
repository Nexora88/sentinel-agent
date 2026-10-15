"""
Ollama client wrapper for Sentinel Agent.
No external paid APIs — only local / self-hosted Ollama.
"""

from __future__ import annotations

import os
import ipaddress
from urllib.parse import urlparse
from typing import Any, List, Optional, Union

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


def validate_local_ollama_url(base_url: str) -> str:
    """Reject remote/cloud model endpoints; SEKA inference must remain on this device."""
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("OLLAMA_BASE_URL must be a local http:// endpoint without credentials.")
    host = parsed.hostname.lower().rstrip(".")
    # These exact hostnames are service-local DNS names inside the supplied Docker network.
    if host in {"host.docker.internal", "ollama"}:
        return base_url.rstrip("/")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if host == "localhost" or (address is not None and address.is_loopback):
        return base_url.rstrip("/")
    raise ValueError(
        "Remote Ollama endpoints are disabled. Use localhost/loopback or host.docker.internal "
        "for a local Docker deployment."
    )


class OllamaClient:
    """Simple and reliable Ollama interface."""

    def __init__(
        self,
        model: Optional[str] = None,
        embed_model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.2,
    ):
        self.base_url = validate_local_ollama_url(base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        self.mkaos_enabled = os.getenv("MKAOS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        self.chat_base_url = (
            validate_local_ollama_url(os.getenv("MKAOS_BASE_URL", "http://127.0.0.1:11435"))
            if self.mkaos_enabled else self.base_url
        )
        # MKAOS only replaces chat generation. Embeddings deliberately remain on the
        # configured local Ollama endpoint until MKAOS has a separately validated embedder.
        self.model_name = (
            os.getenv("MKAOS_MODEL_NAME", "mkaos-local")
            if self.mkaos_enabled else (model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b"))
        )
        self.embed_model_name = embed_model or os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self.temperature = temperature

        self._llm: Optional[ChatOllama] = None
        self._embeddings: Optional[OllamaEmbeddings] = None

    @property
    def llm(self) -> ChatOllama:
        if self._llm is None:
            self._llm = ChatOllama(
                model=self.model_name,
                base_url=self.chat_base_url,
                temperature=self.temperature,
            )
        return self._llm

    @property
    def embeddings(self) -> OllamaEmbeddings:
        if self._embeddings is None:
            self._embeddings = OllamaEmbeddings(
                model=self.embed_model_name,
                base_url=self.base_url,
            )
        return self._embeddings

    def chat(
        self,
        prompt_or_messages: Union[str, List[dict]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Chat with either a simple string or a list of role/content dicts."""
        messages = []

        if isinstance(prompt_or_messages, list):
            for m in prompt_or_messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                if role == "system":
                    messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
                else:
                    messages.append(HumanMessage(content=content))
        else:
            if system:
                messages.append(SystemMessage(content=system))
            messages.append(HumanMessage(content=prompt_or_messages))

        llm = self.llm
        if temperature is not None:
            llm = llm.bind(temperature=temperature)

        response = llm.invoke(messages)
        return response.content

    def get_crew_llm(self):
        """Return CrewAI's local Ollama adapter; never fall back to a hosted provider."""
        from crewai import LLM

        # CrewAI's current Agent schema does not accept LangChain ChatOllama directly.
        # The explicit ollama/ provider and validated local base_url keep inference local.
        return LLM(
            model=f"ollama/{self.model_name}",
            base_url=self.chat_base_url,
            temperature=self.temperature,
        )
