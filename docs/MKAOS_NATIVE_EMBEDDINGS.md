# MKAOS native embeddings — experimental offline baseline

MKAOS can run the RAG/Chroma embedding interface without contacting an
embedding model server by setting:

```env
SEKA_EMBEDDINGS_PROVIDER=mkaos-native
```

The implementation in `core/native_embeddings.py` uses deterministic signed
hashing over Unicode word unigrams, word bigrams, and character 3–5-grams. It
has no downloaded weights, API, network connection, or per-run training. Stable
hashing and normalized vectors make it useful as a reproducible offline lexical
retrieval baseline, including for Turkish suffix variation.

**Important limitation:** this is not a neural semantic model and does not make
MKAOS a trained language model. Lexical overlap is not semantic understanding;
the baseline may rank paraphrases or conceptually related documents poorly.
The default is `SEKA_EMBEDDINGS_PROVIDER=mkaos-native` to permit offline operation. This is an operational-independence choice, not a claim that retrieval quality matches a trained embedding model; follow the evaluation gates below before claiming semantic parity.

## Reproducible smoke benchmark

Run the small, fixed, authored Turkish test set:

```bash
SEKA_EMBEDDINGS_PROVIDER=mkaos-native python -m scripts.benchmark_mkaos_retrieval
```

If the configured local Ollama embedding server is available, run the same
queries and corpus for a first comparison:

```bash
SEKA_EMBEDDINGS_PROVIDER=ollama python -m scripts.benchmark_mkaos_retrieval
```

The script reports Recall@1/3/5, MRR@10, nDCG@10, empty-query count, and query
latency. CI runs the native smoke benchmark. The dataset is only 12 synthetic,
human-authored examples: it checks that the pipeline behaves and produces
repeatable measurements, **not** general Turkish semantic quality or parity
with Ollama. Production decisions require a larger, reviewed, provenance-
tracked dataset and same-machine comparisons. RAM and disk footprint should
also be measured on target hardware before claiming performance parity.

## Validation gates before removing Ollama

1. Freeze a licensed, provenance-tracked Turkish retrieval corpus with query,
   relevant-document IDs, and difficult negative examples.
2. Report Recall@1/3/5, MRR@10, nDCG@10, latency, RAM, and disk footprint for
   both providers on the same corpus, chunking, and retrieval settings.
3. Require no cross-tenant retrieval, persistence/restart compatibility, and
   offline tests. Automated tests now cover native-mode persistence/reopen and
   tenant-scoped retrieval; these are regression checks, not proof of complete
   production isolation.
4. Verify offline operation with network-level controls/packet capture on a
   target deployment; a configuration flag alone is insufficient.
5. Provider-specific Chroma collection names keep vectors from different embedding spaces isolated. Existing collections remain available under their original provider namespace; migrate/re-index deliberately rather than mixing incompatible vectors.
6. Only then decide whether a trained MKAOS-owned embedding model is needed.
   This hashing baseline alone is not evidence of parity.

Native hashing is now the default provider so the RAG path does not instantiate or contact Ollama. Set `SEKA_EMBEDDINGS_PROVIDER=ollama` only when explicitly choosing the legacy embedding model. Unknown provider values fail closed. Chat generation remains MKAOS-only and has no Ollama chat fallback. This removes the runtime dependency, not the quality gap: native hashing remains a lexical baseline and must not be described as neural semantic embeddings.
