"""
MKAOS-only chat client. Ollama is temporarily retained only for embeddings.
A failed MKAOS request is surfaced; chat never falls back to another runtime.
"""
from __future__ import annotations
import os
import ipaddress
from urllib.parse import urlparse
from typing import List, Optional, Union
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

def validate_local_ollama_url(base_url: str) -> str:
    """Validate a local-only HTTP endpoint, including MKAOS Compose DNS."""
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Model endpoints must be local http:// URLs without credentials.")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"host.docker.internal", "ollama", "mkaos", "localhost"}:
        return base_url.rstrip("/")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and address.is_loopback:
        return base_url.rstrip("/")
    raise ValueError("Remote model endpoints are disabled; use loopback or trusted local Docker service names.")

class OllamaClient:
    """Compatibility wrapper: MKAOS chat plus temporary local Ollama embeddings."""
    def __init__(self, model: Optional[str] = None, embed_model: Optional[str] = None,
                 base_url: Optional[str] = None, temperature: Optional[float] = None):
        # base_url is used only by the legacy embedding adapter, never for chat.
        self.base_url = validate_local_ollama_url(base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        self.chat_base_url = validate_local_ollama_url(os.getenv("MKAOS_BASE_URL", "http://127.0.0.1:11435"))
        self.mkaos_enabled = True
        self.model_name = os.getenv("MKAOS_MODEL_NAME", "mkaos-local")
        self.embed_model_name = embed_model or os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self.temperature = temperature if temperature is not None else float(os.getenv("MKAOS_TEMPERATURE", "0.15"))
        self.repetition_penalty = float(os.getenv("MKAOS_REPETITION_PENALTY", "1.10"))
        self.top_p = float(os.getenv("MKAOS_TOP_P", "0.9"))
        self._llm: Optional[ChatOllama] = None
        self._embeddings: Optional[OllamaEmbeddings] = None

    @property
    def llm(self) -> ChatOllama:
        if self._llm is None:
            self._llm = ChatOllama(model=self.model_name, base_url=self.chat_base_url,
                temperature=self.temperature, repeat_penalty=self.repetition_penalty, top_p=self.top_p)
        return self._llm

    @property
    def embeddings(self) -> OllamaEmbeddings:
        """Temporary local embedding adapter; remove when native MKAOS embeddings pass parity tests."""
        if self._embeddings is None:
            self._embeddings = OllamaEmbeddings(model=self.embed_model_name, base_url=self.base_url)
        return self._embeddings

    def chat(self, prompt_or_messages: Union[str, List[dict]], system: Optional[str] = None,
             temperature: Optional[float] = None) -> str:
        """Generate through MKAOS only; runtime errors intentionally propagate."""
        messages = []
        if isinstance(prompt_or_messages, list):
            for message in prompt_or_messages:
                role, content = message.get("role", "user"), message.get("content", "")
                if role == "system": messages.append(SystemMessage(content=content))
                elif role == "assistant": messages.append(AIMessage(content=content))
                else: messages.append(HumanMessage(content=content))
        else:
            if system: messages.append(SystemMessage(content=system))
            messages.append(HumanMessage(content=prompt_or_messages))
        llm = self.llm
        if temperature is not None: llm = llm.bind(temperature=temperature)
        return llm.invoke(messages).content

    def get_crew_llm(self):
        """CrewAI compatibility adapter pointed only at MKAOS's local API."""
        from crewai import LLM
        return LLM(model=f"ollama/{self.model_name}", base_url=self.chat_base_url,
            temperature=self.temperature, top_p=self.top_p, repeat_penalty=self.repetition_penalty)
