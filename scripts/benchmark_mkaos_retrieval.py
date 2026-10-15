"""Reproducible, synthetic Turkish RAG retrieval benchmark.

Run native:
  SEKA_EMBEDDINGS_PROVIDER=mkaos-native python scripts/benchmark_mkaos_retrieval.py

Run the Ollama comparison (requires the configured local embedding server):
  SEKA_EMBEDDINGS_PROVIDER=ollama python scripts/benchmark_mkaos_retrieval.py

The corpus is authored test material, not a representative production dataset.
Results must not be presented as a general semantic-quality claim.
"""
from __future__ import annotations

import json
import os
import statistics
import tempfile
import time
from pathlib import Path

from core.rag import MemoryStore

# Small, fixed, human-authored smoke benchmark. Expand only with licensed,
# provenance-tracked examples and reviewed relevance labels.
DOCUMENTS = [
    ("bees_winter", "Arıların kış bakımı için kovan havalandırması, nem kontrolü ve yeterli bal stoğu önemlidir."),
    ("bees_honey", "Bal akımı döneminde nektar kaynakları, hava koşulları ve koloninin gücü bal verimini etkiler."),
    ("bees_varroa", "Varroa mücadelesinde ruhsatlı uygulamalar, doğru zamanlama ve koloni takibi önem taşır."),
    ("fire_safety", "Orman yangını riskini sıcaklık, rüzgâr, bağıl nem ve kuraklık birlikte etkiler."),
    ("fire_satellite", "Uydu sıcak nokta verileri olası yangınları işaret edebilir; tek başına doğrulanmış yangın kanıtı değildir."),
    ("farm_irrigation", "Sulama planı bitki türü, toprak nemi, yağış tahmini ve gelişim evresine göre hazırlanmalıdır."),
    ("farm_ndvi", "NDVI bitki örtüsünün yeşilliği ve canlılığı hakkında uzaktan algılama göstergesi sağlar."),
    ("finance_balance", "Şirket bilançosunda varlıklar, yükümlülükler, özkaynak ve dönem kârı incelenir."),
    ("finance_dividend", "Temettü verimi hisse fiyatı ve yıllık temettü tutarı kullanılarak hesaplanır."),
    ("security_tenant", "Kullanıcı bellekleri tenant kimliğiyle ayrılmalı ve arama sorguları aynı tenant ile sınırlandırılmalıdır."),
    ("security_offline", "Çevrimdışı çalışma ağ bağlantısı kapatılarak ayrıca doğrulanmalı; yalnızca ayar adına güvenilmemelidir."),
    ("mkaos_cache", "KV-cache, üretilen tokenların önceki attention anahtar ve değerlerini yeniden kullanır."),
]
QUERIES = [
    ("Arı kovanında kışın nem ve hava dolaşımı nasıl korunur?", "bees_winter"),
    ("Nektar gelişi ve koloni gücü bal hasadını nasıl etkiler?", "bees_honey"),
    ("Varroa paraziti için mücadele ve takip", "bees_varroa"),
    ("Rüzgâr, sıcak hava ve düşük nem yangın tehlikesini nasıl değiştirir?", "fire_safety"),
    ("Uydu sıcak noktasından yangının kesin olduğu söylenebilir mi?", "fire_satellite"),
    ("Tarlada sulama kararını toprak ve hava durumuna göre verme", "farm_irrigation"),
    ("Uydu görüntüsünden bitki yeşilliğini izleme indeksi", "farm_ndvi"),
    ("Bilançodaki borçlar ve öz kaynakların incelenmesi", "finance_balance"),
    ("Hisse fiyatına göre temettü oranı nasıl bulunur?", "finance_dividend"),
    ("Bir kullanıcının hafıza aramasının başka hesaptan bilgi getirmesini engelleme", "security_tenant"),
    ("Ağ kapalıyken uygulamanın gerçekten yerel kaldığını sınama", "security_offline"),
    ("Üretimde önceki attention hesaplarını tekrar kullanma", "mkaos_cache"),
]


def dcg(relevances: list[int]) -> float:
    import math
    return sum(rel / math.log2(index + 2) for index, rel in enumerate(relevances))


def main() -> int:
    provider = os.getenv("SEKA_EMBEDDINGS_PROVIDER", "ollama").strip().lower()
    with tempfile.TemporaryDirectory(prefix="mkaos-rag-bench-") as tmp:
        store = MemoryStore(
            collection_name="mkaos_retrieval_benchmark",
            persist_directory=str(Path(tmp) / "chroma"),
        )
        store.add_texts(
            [body for _, body in DOCUMENTS],
            [{"source": doc_id, "type": "benchmark"} for doc_id, _ in DOCUMENTS],
        )

        reciprocal_ranks: list[float] = []
        recalls: dict[int, list[float]] = {1: [], 3: [], 5: []}
        ndcgs: list[float] = []
        latencies_ms: list[float] = []
        failures = 0

        for query, relevant_id in QUERIES:
            started = time.perf_counter()
            try:
                results = store.search(query, k=10)
            except Exception:
                results = []
            latencies_ms.append((time.perf_counter() - started) * 1000)
            ranked_ids = [str(doc.metadata.get("source", "")) for doc in results]
            if not ranked_ids:
                failures += 1
            rank = ranked_ids.index(relevant_id) + 1 if relevant_id in ranked_ids else None
            reciprocal_ranks.append(1.0 / rank if rank else 0.0)
            for k in recalls:
                recalls[k].append(float(relevant_id in ranked_ids[:k]))
            ndcgs.append(dcg([int(doc_id == relevant_id) for doc_id in ranked_ids[:10]]))

        report = {
            "provider": provider,
            "dataset": "authored_synthetic_tr_v1",
            "documents": len(DOCUMENTS),
            "queries": len(QUERIES),
            "failed_or_empty_queries": failures,
            "recall_at_k": {str(k): round(statistics.mean(values), 4) for k, values in recalls.items()},
            "mrr_at_10": round(statistics.mean(reciprocal_ranks), 4),
            "ndcg_at_10": round(statistics.mean(ndcgs), 4),
            "mean_query_latency_ms": round(statistics.mean(latencies_ms), 3),
            "p95_query_latency_ms": round(sorted(latencies_ms)[min(len(latencies_ms) - 1, int(0.95 * len(latencies_ms)))], 3),
            "limitations": [
                "small synthetic smoke set; not a representative Turkish evaluation corpus",
                "run each provider against the same frozen corpus and labels for comparison",
                "does not test production data, cross-process restart, or network isolation",
            ],
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
