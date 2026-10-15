"""Deterministic, fully local lexical embeddings for MKAOS retrieval experiments.

This is a transparent character/word n-gram hashing baseline, not a trained
semantic embedding model. It supports offline retrieval without a model server,
but must pass the repository's retrieval-quality gate before replacing the
current embedding provider by default.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable

from langchain_core.embeddings import Embeddings

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


class NativeHashEmbeddings(Embeddings):
    """Stable signed feature-hashing embeddings; no network or model weights."""

    def __init__(self, dimensions: int = 768):
        if not isinstance(dimensions, int) or dimensions < 128 or dimensions > 8192:
            raise ValueError("dimensions must be an integer in [128, 8192]")
        self.dimensions = dimensions

    @staticmethod
    def _features(text: str) -> Iterable[tuple[str, float]]:
        normalized = " ".join(_WORD_RE.findall(text.casefold()))
        words = normalized.split()
        for word in words:
            yield "w:" + word, 2.0
        for left, right in zip(words, words[1:]):
            yield "b:" + left + "_" + right, 1.5
        # Character n-grams preserve Turkish inflections and tolerate minor typos.
        for word in words:
            padded = "^" + word + "$"
            for n in (3, 4, 5):
                for start in range(max(0, len(padded) - n + 1)):
                    yield f"c{n}:" + padded[start:start + n], 1.0

    def _embed(self, text: str) -> list[float]:
        if not isinstance(text, str):
            raise TypeError("embedding input must be a string")
        vector = [0.0] * self.dimensions
        for feature, weight in self._features(text):
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:8], "little") % self.dimensions
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign * weight
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
