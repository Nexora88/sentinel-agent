# MKAOS native embeddings — experimental offline baseline

MKAOS can now run the RAG/Chroma embedding interface without contacting an
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
The default remains `SEKA_EMBEDDINGS_PROVIDER=ollama` until the native path
passes a larger, frozen Turkish retrieval benchmark.

## Validation gates before removing Ollama

1. Freeze a licensed, provenance-tracked Turkish retrieval corpus with query,
   relevant-document IDs, and difficult negative examples.
2. Report Recall@1/3/5, MRR@10, nDCG@10, latency, RAM, and disk footprint.
3. Compare the native baseline against the current embedding path on identical
   corpus, chunking, queries, and retrieval settings.
4. Require no cross-tenant retrieval, persistence/restart compatibility, and
   offline tests. Existing Chroma collections created with another embedding
   space must be re-indexed; never silently mix incompatible vectors.
5. Only then decide whether a trained MKAOS-owned embedding model is needed.
   This hashing baseline alone is not evidence of parity.

The environment variable is opt-in; unknown provider values fail closed. Chat
generation remains MKAOS-only and has no Ollama fallback.
