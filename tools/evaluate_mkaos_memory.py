#!/usr/bin/env python3
"""Evaluate MKAOS memory retrieval on a small, transparent Turkish smoke set.

This is a regression/smoke benchmark, not an independent scientific evaluation.
It forces the native local embedding provider and writes latency + ranking metrics.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

CASES = [
    {"id": "edr_soil", "text": "Edirne tarlasında toprak nemi ölçümü yapılmalı; kuru toprak sulama ihtiyacını gösterebilir.", "query": "Edirne tarlalarının toprağı kuru mu, nem ölçümü ve sulama", "expected": "edr_soil"},
    {"id": "mkaos_cache", "text": "MKAOS bellek araması tekrar eden sorguları kısa süreli önbellekte tutar; yeni bilgi kaydedilince önbellek temizlenir.", "query": "MKAOS yeni bilgi öğrenince eski bellek önbelleği ne olur", "expected": "mkaos_cache"},
    {"id": "tr_ankara", "text": "Türkiye'nin başkenti Ankara'dır.", "query": "Türkiye'nin başkenti hangi şehir", "expected": "tr_ankara"},
    {"id": "kv_cache", "text": "Rust çıkarım motorunda artımlı KV cache, önceki tokenların anahtar ve değerlerini tekrar kullanır.", "query": "Rust motoru KV önbelleği önceki tokenları nasıl kullanıyor", "expected": "kv_cache"},
    {"id": "offline", "text": "Çevrimdışı kipte ağ çağrısı yapılmamalı; yerel model ve yerel bellek kullanılmalıdır.", "query": "İnternet bağlantısı yokken yerel sistem nasıl çalışmalı", "expected": "offline"},
    {"id": "tenant", "text": "Kiracı izolasyonu için her kullanıcının hafıza sorgusu yalnızca kendi tenant kimliğine ait kayıtları görmelidir.", "query": "Bir kullanıcının belleği diğer hesaba görünmesin", "expected": "tenant"},
    {"id": "ollama", "text": "Ollama gömmeleri varsayılan olmaktan ancak yerel gömme kalitesi ölçümlerle yeterli bulunduğunda çıkarılmalıdır.", "query": "Ollama embedding yerine yerel sistem ne zaman seçilmeli", "expected": "ollama"},
    {"id": "turkish", "text": "Türkçe aramada ı, İ, ş, ğ, ç, ö ve ü karakterleri korunmalı; ekli kelimeler de değerlendirilmelidir.", "query": "Türkçe karakterler ve kelime ekleri hafıza aramasında önemli", "expected": "turkish"},
]


def summarize(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "median_ms": None, "p95_ms": None}
    ordered = sorted(values)
    p95_pos = (len(ordered) - 1) * 0.95
    lo, hi = int(p95_pos), min(int(p95_pos) + 1, len(ordered) - 1)
    p95 = ordered[lo] + (ordered[hi] - ordered[lo]) * (p95_pos - lo)
    return {
        "count": len(values),
        "median_ms": round(statistics.median(values), 3),
        "p95_ms": round(p95, 3),
    }


def score_ranking(found_ids: list[str], expected_id: str, k: int) -> dict[str, float]:
    rank = found_ids.index(expected_id) + 1 if expected_id in found_ids else None
    return {
        "recall_at_k": 1.0 if rank is not None and rank <= k else 0.0,
        "reciprocal_rank": 1.0 / rank if rank is not None else 0.0,
        "answer_context_hit": 1.0 if rank == 1 else 0.0,
    }


def evaluate(output: str | None = None, k: int = 3) -> dict[str, Any]:
    # Ensure no embedding daemon or network model is needed for this evaluation.
    os.environ["SEKA_EMBEDDINGS_PROVIDER"] = "mkaos-native"
    from core.rag import MemoryStore

    with tempfile.TemporaryDirectory(prefix="mkaos-memory-eval-") as temp:
        store = MemoryStore(
            collection_name="mkaos_eval",
            persist_directory=str(Path(temp) / "chroma"),
            tenant_id="eval-tenant",
        )
        store.add_texts(
            [case["text"] for case in CASES],
            [{"source": case["id"], "case_id": case["id"], "tenant_id": "eval-tenant"} for case in CASES],
        )
        rows = []
        cold_ms: list[float] = []
        warm_ms: list[float] = []
        for case in CASES:
            start = time.perf_counter()
            docs = store.search(case["query"], k=k)
            cold_ms.append((time.perf_counter() - start) * 1000)
            found = [str(doc.metadata.get("case_id", doc.metadata.get("source", ""))) for doc in docs]
            scores = score_ranking(found, case["expected"], k)
            # A repeated identical query tests the bounded result cache independently of ranking.
            start = time.perf_counter()
            warm_docs = store.search(case["query"], k=k)
            warm_ms.append((time.perf_counter() - start) * 1000)
            rows.append({
                "query_id": case["id"], "expected_id": case["expected"],
                "top_k_ids": found, **scores,
                "cache_repeat_same_ids": found == [
                    str(doc.metadata.get("case_id", doc.metadata.get("source", ""))) for doc in warm_docs
                ],
            })
        denominator = max(1, len(rows))
        report = {
            "benchmark": "MKAOS Turkish memory smoke v1",
            "scope_note": "Small curated smoke set; not an independent or production-quality benchmark.",
            "provider": store.embedding_provider,
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cases": len(rows),
            "k": k,
            "recall_at_k": round(sum(row["recall_at_k"] for row in rows) / denominator, 4),
            "mrr": round(sum(row["reciprocal_rank"] for row in rows) / denominator, 4),
            "answer_context_hit_rate": round(sum(row["answer_context_hit"] for row in rows) / denominator, 4),
            "cold_query_latency": summarize(cold_ms),
            "repeat_query_latency": summarize(warm_ms),
            "cache_repeat_consistency": all(row["cache_repeat_same_ids"] for row in rows),
            "cache_stats": store.stats(),
            "results": rows,
        }
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(serialized + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Optional JSON report path")
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.k <= 8:
        parser.error("--k must be between 1 and 8")
    report = evaluate(args.output, args.k)
    print(json.dumps({key: report[key] for key in (
        "benchmark", "provider", "cases", "k", "recall_at_k", "mrr",
        "answer_context_hit_rate", "cold_query_latency", "repeat_query_latency",
        "cache_repeat_consistency",
    )}, ensure_ascii=False, indent=2))
    return 0 if report["cache_repeat_consistency"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
