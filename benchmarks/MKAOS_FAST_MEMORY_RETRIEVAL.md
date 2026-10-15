# MKAOS fast response and local-memory retrieval milestone

## Implemented in this branch

- Bounded hybrid retrieval: vector-store candidates are reranked using semantic/vector rank and Unicode-aware lexical overlap.
- Turkish Unicode tokenization, including dotted/dotless i and other Turkish letters.
- Short-lived per-process LRU result cache (30-second TTL, maximum 128 entries).
- Cache invalidation after ingestion and a memory-generation key.
- Cache counters and retrieval mode in `MemoryStore.stats()`.
- `tools/evaluate_mkaos_memory.py` evaluates a transparent, curated Turkish smoke set with Recall@k, MRR, answer-context hit rate, cold-query latency, repeat-query latency and cache consistency. It forces `SEKA_EMBEDDINGS_PROVIDER=mkaos-native` and needs no Ollama embedding daemon.

## Run the memory evaluation

```bash
python tools/evaluate_mkaos_memory.py --k 3 --output artifacts/mkaos-memory-evaluation.json
python -m unittest tests.test_mkaos_memory_evaluation tests.test_hybrid_memory_retrieval
```

The eight-case set is a regression smoke test, not an independent or production-quality benchmark. Review the per-query rankings and repeat on a held-out Turkish set before changing the default embedding provider.

## Rust inference / KV-cache validation

The Rust tests compare cached incremental logits against fresh-prefix recomputation on deterministic synthetic weights and compare greedy token sequences between cached and reference generation. Run:

```bash
cargo test --manifest-path engine/mkaos-inference/Cargo.toml
cargo test --manifest-path engine/mkaos-hf-adapter/Cargo.toml
```

These validate algorithmic consistency, not production throughput or compatibility with arbitrary pretrained model weights. Use `tools/benchmark_mkaos_device.py` on the target physical device to measure cold-start time, time to first response, per-request latency, token throughput, and memory usage. CI-host numbers are not substitutes for the user's device.

## Sovereignty gate

The native hash/character n-gram embedding is local and deterministic, but it is not a trained semantic embedding model. Ollama remains the default until a reviewed held-out Turkish evaluation demonstrates adequate retrieval quality and offline tests pass. Full sovereignty also requires a compatible, trained owned language model, tokenizer and model weights, license/provenance review, and network-isolation evidence. These are not declared complete by this benchmark.
