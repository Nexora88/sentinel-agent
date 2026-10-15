# MKAOS fast response and local-memory retrieval milestone

This milestone improves the existing two local paths without claiming a stronger model than the weights can support.

## Memory retrieval

core/rag.py now:
- uses a bounded candidate pool from the configured local vector store, then reranks with both vector rank and Unicode-aware lexical overlap;
- keeps Turkish letters and inflected forms in lexical matching;
- caches repeated (tenant, query, k) searches in a per-process LRU cache for 30 seconds (128 entries maximum);
- clears the cache immediately after ingestion so a newly learned fact is not hidden by stale results;
- exposes cache counters and retrieval mode through MemoryStore.stats().

The cache stores results only in process memory; it does not persist prompts or query text. Tenant identity remains part of the cache key and the vector-store filter. Existing Chroma persistence remains local.

## Two engine tracks

1. **Chat/inference engine:** MKAOS remains the only chat route. The Rust reference decoder already exposes incremental KV-cache generation; this milestone does not claim production throughput or a validated owned checkpoint.
2. **Memory/embedding engine:** SEKA_EMBEDDINGS_PROVIDER=mkaos-native selects the deterministic local hash/character n-gram embedding baseline. It avoids the Ollama embedding service, but is lexical rather than a trained semantic model. The default stays unchanged until retrieval-quality tests on a reviewed Turkish dataset justify switching it.

## Validation required before production claims

- Run the full Python and Rust CI on this commit.
- Compare recall@k, MRR, answer-context hit rate and latency on a held-out Turkish memory set, including spelling variations and inflections.
- Benchmark first-query and cache-hit latency on target hardware, with corpus size and environment recorded.
- Verify tenant isolation and that ingestion invalidates cache entries.
- Test KV-cache token/logit parity against uncached generation and benchmark TTFT separately from total generation time.
- Keep the existing external model/embedding comparison until quality, latency, offline, and license gates pass.

A cache hit is a speed optimization, not improved model intelligence. Hash embeddings are not represented as a replacement for a trained semantic embedding model until the measured retrieval gate passes.
