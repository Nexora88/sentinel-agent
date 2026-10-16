"""Bounded hybrid reranking for local RAG.

Dense retrieval supplies candidates; this module reorders only those candidates
using reciprocal-rank fusion and a small BM25-style lexical signal. It never
pretends that lexical hashing is semantic understanding and never crosses the
tenant filter applied by the caller.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Sequence

from langchain_core.documents import Document

_TOKEN_RE = re.compile(r"[^\\W_]+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold().replace("\u0307", "")
    return _TOKEN_RE.findall(normalized)


def _bm25_scores(query: str, documents: Sequence[Document]) -> list[float]:
    query_terms = list(dict.fromkeys(_tokens(query)))
    token_rows = [_tokens(doc.page_content) for doc in documents]
    if not query_terms or not token_rows:
        return [0.0] * len(documents)

    lengths = [len(row) for row in token_rows]
    average_length = sum(lengths) / max(1, len(lengths))
    document_frequency = Counter(
        term for term in query_terms
        for present in [{token for token in row if token == term}]
        if present
    )
    scores = []
    for row, length in zip(token_rows, lengths):
        counts = Counter(row)
        score = 0.0
        for term in query_terms:
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            df = sum(1 for candidate in token_rows if term in candidate)
            inverse = math.log(1.0 + (len(token_rows) - df + 0.5) / (df + 0.5))
            denominator = frequency + 1.2 * (1.0 - 0.75 + 0.75 * length / max(1.0, average_length))
            score += inverse * frequency * 2.2 / denominator
        scores.append(score)
    return scores


def hybrid_rerank(
    query: str,
    dense_documents: Sequence[Document],
    *,
    limit: int = 6,
    dense_weight: float = 0.65,
    lexical_weight: float = 0.35,
) -> list[Document]:
    """Rerank a bounded dense candidate set; preserve stable ordering for ties."""
    if not isinstance(query, str) or not query.strip() or not dense_documents:
        return []
    if not 1 <= int(limit) <= 100:
        raise ValueError("limit must be between 1 and 100")
    if dense_weight < 0 or lexical_weight < 0 or dense_weight + lexical_weight <= 0:
        raise ValueError("reranking weights must be non-negative and not both zero")

    candidates = list(dense_documents)
    raw_lexical = _bm25_scores(query, candidates)
    maximum = max(raw_lexical, default=0.0)
    lexical = [score / maximum if maximum > 0 else 0.0 for score in raw_lexical]
    weight_total = dense_weight + lexical_weight
    scored = []
    for index, (document, lexical_score) in enumerate(zip(candidates, lexical)):
        dense_rank_score = 1.0 - (index / max(1, len(candidates)))
        fused = (
            dense_weight * dense_rank_score + lexical_weight * lexical_score
        ) / weight_total
        scored.append((fused, index, document))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [document for _, _, document in scored[:int(limit)]]
