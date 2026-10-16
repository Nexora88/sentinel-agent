# MKAOS hybrid RAG quality gates

## What changed

\`core/rag.py\` now retrieves a bounded candidate pool (up to 4× the requested top-k, capped at 100) and optionally reranks it with \`core/hybrid_rag.py\`. The reranker blends dense retrieval order with a BM25-style lexical signal. This is intended to recover useful exact-term evidence without discarding the embedding model's candidate order.

- Enabled by default; set \`SEKA_RAG_HYBRID_RERANK=false\` to compare against dense-only order.
- Tenant filtering is applied before reranking. The reranker cannot add documents outside the candidate set.
- Candidate retrieval remains bounded; this does not scan the entire corpus.
- Existing source metadata is preserved so answer generation can cite retrieved evidence.
- Tests cover ranking, Turkish dotted-I normalization, tie stability, and argument bounds.

## Honest capability labels

| Provider | What it does | What it does not prove |
| --- | --- | --- |
| \`mkaos-native\` | Offline signed word/bigram/character n-gram vectors | It is not a trained semantic encoder; paraphrase understanding is limited |
| \`local-semantic\` | Runs a pre-installed local Sentence-Transformers model with remote loading disabled | Model rights, quality, and performance still require separate review |
| \`ollama\` | Uses the configured Ollama embedding endpoint | It is not an independent local encoder and is not the default sovereign path |

Hybrid reranking improves ordering among retrieved candidates; it cannot recover a semantically relevant document that never enters the candidate pool. A genuine semantic quality claim requires a licensed local embedding model or an MKAOS-trained encoder, plus held-out Turkish retrieval evaluation.

## Evaluation protocol for the reported 5.5/10 result

Do not compare one overall score without its task breakdown. Keep a small, versioned held-out set (start with 100–300 human-reviewed Turkish query/relevant-document pairs, not millions of documents), split by topic and prevent duplicate or near-duplicate leakage. Include:
- paraphrases and synonym substitutions;
- Turkish suffixes, dotted/dotless I, spelling variants, and typos;
- multi-hop queries where more than one source is needed;
- hard negatives from adjacent topics;
- abstention cases where the corpus contains no answer.

Report Recall@1/3/5, MRR@10, nDCG@10, citation/source correctness, answer faithfulness, unsupported-claim rate, p50/p95 latency, RAM, disk footprint, and model/provider identity. Compare native baseline, hybrid native, local semantic dense-only, and local semantic hybrid on the *same* fixed split. Keep the test split out of training and tune weights only on a validation split.

## Lightweight capacity and training

Do not increase parameter count merely to make a configuration number larger. Keep the existing 1B and 1.5B profiles as planning targets, then use a small, rights-cleared pilot to measure tokens/sec, peak RAM/VRAM, validation loss, and Turkish task scores before committing to full training. Better tokenization, clean high-signal examples, longer-context correctness, and training stability can outperform a larger poorly trained checkpoint. A 1B–1.5B training run has not been performed by this change.

## Release gates

1. Human-review and record source-specific training rights, privacy, attribution, and model-weight redistribution policy.
2. Pin the local embedding model files and inventory manifest; test offline loading on CPU.
3. Run the held-out benchmark and retain machine-readable results plus environment and hardware metadata.
4. Verify tenant isolation and PostgreSQL persistence in live integration CI before switching application traffic.
5. Never label lexical hash vectors as semantic embeddings, or a test pass as proof that the model's reasoning score improved.
