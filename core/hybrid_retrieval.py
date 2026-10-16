"""Deterministic, network-free hybrid reranking for local MKAOS RAG.

This combines the existing local vector/feature-hash candidate order with a
small BM25-style lexical score. It is a retrieval improvement, NOT a semantic
embedding model and does not claim paraphrase understanding.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Any, Sequence

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def _normalize(text: str) -> str:
    # Apply Turkish casing before casefold so dotted/dotless I remain distinct.
    text = text.replace("İ", "i").replace("I", "ı")
    return unicodedata.normalize("NFKC", text).casefold()


def tokenize(text: str) -> list[str]:
    """Return stable Unicode word tokens without external NLP dependencies."""
    return _TOKEN_RE.findall(_normalize(text))


def _bm25_scores(query: str, documents: Sequence[Any]) -> list[float]:
    query_terms = tokenize(query)
    if not query_terms or not documents:
        return [0.0] * len(documents)

    token_rows = [tokenize(str(getattr(doc, "page_content", ""))) for doc in documents]
    lengths = [len(row) for row in token_rows]
    average_length = sum(lengths) / max(1, len(lengths))
    document_frequency: Counter[str] = Counter()
    term_counts = [Counter(row) for row in token_rows]
    for row in token_rows:
        document_frequency.update(set(row))

    total = len(token_rows)
    k1, b = 1.2, 0.75
    scores: list[float] = []
    for counts, length in zip(term_counts, lengths):
        score = 0.0
        for term in query_terms:
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            df = document_frequency[term]
            inverse = math.log(1.0 + (total - df + 0.5) / (df + 0.5))
            denominator = frequency + k1 * (
                1.0 - b + b * length / max(1.0, average_length)
            )
            score += inverse * frequency * (k1 + 1.0) / denominator
        scores.append(score)
    return scores


def rerank_local_candidates(query: str, documents: Sequence[Any], limit: int) -> list[Any]:
    """Fuse vector-candidate rank with local BM25 rank using reciprocal-rank fusion.

    Input order is the rank supplied by the local vector store. RRF avoids
    comparing unlike raw score scales and preserves vector rank when lexical
    evidence is absent. Stable tie-breaking keeps repeated runs reproducible.
    """
    if not isinstance(query, str) or not query.strip() or limit <= 0:
        return []
    candidates = list(documents)
    if not candidates:
        return []

    lexical_scores = _bm25_scores(query, candidates)
    lexical_order = sorted(
        range(len(candidates)), key=lambda index: (-lexical_scores[index], index)
    )
    lexical_rank = {index: rank + 1 for rank, index in enumerate(lexical_order)}
    rrf_constant = 60.0
    fused = []
    for vector_index, document in enumerate(candidates):
        score = 1.0 / (rrf_constant + vector_index + 1)
        if lexical_scores[vector_index] > 0:
            score += 1.0 / (rrf_constant + lexical_rank[vector_index])
        fused.append((score, vector_index, document))
    fused.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in fused[:limit]]
