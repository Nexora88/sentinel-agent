"""
Ollama client wrapper for Sentinel Agent.
No external paid APIs — only local / self-hosted Ollama.
"""

from __future__ import annotations

import os
from typing import Any, List, Optional, Union

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


class OllamaClient:
    """Simple and reliable Ollama interface."""

    def __init__(
        self,
        model: Optional[str] = None,
        embed_model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.2,
    ):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = model or os.getenv("OLLAMA_MODEL", "qwen2.5-coder:32b")
        self.embed_model_name = embed_model or os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self.temperature = temperature

        self._llm: Optional[ChatOllama] = None
        self._embeddings: Optional[OllamaEmbeddings] = None

    @property
    def llm(self) -> ChatOllama:
        if self._llm is None:
            self._llm = ChatOllama(
                model=self.model_name,
                base_url=self.base_url,
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
        """Return LLM compatible with CrewAI."""
        return self.llm
