# MKAOS: Turkish-first learning and capability roadmap

This roadmap separates software capability from model knowledge. A tokenizer, retrieval index, or reasoning scaffold does not by itself make the model knowledgeable; claims must be backed by measurable evaluations.

## Workstream A — runtime speed and correctness

1. Run the release benchmark on the same machine before and after each change:
   `cargo run --release --manifest-path engine/mkaos-inference/Cargo.toml --example mkaos_cpu_bench`
2. Save the complete stdout with CPU model, OS, Rust version, commit SHA, and power profile. Compare medians; do not compare unrelated runners.
3. Add optimized matrix multiplication behind a backend boundary while keeping the current safe scalar implementation as a correctness oracle.
4. Validate each backend on deterministic matrices (including odd sizes, zeros, negative values, and large/small magnitudes) using absolute and relative error tolerances.
5. Add model-level tests for cache vs full-prefix logits, greedy token parity, sequence boundaries, and malformed checkpoints.
6. Only then profile allocation count, memory high-water mark, prefill latency, decode latency/token, and throughput.

## Workstream B — native Turkish tokenizer

Current `ByteTokenizer` is a valid small baseline, not a modern language-model tokenizer. It uses UTF-8 bytes and a 257-token vocabulary; it is incompatible with SmolLM2's tokenizer.

- Specify a versioned tokenizer artifact and stable special-token IDs before training.
- Build tokenizer training only from a rights-cleared corpus; keep tokenizer-training data manifests and hashes.
- Test Turkish-specific cases: `İ ı Ş ş Ğ ğ Ç ç Ö ö Ü ü`, apostrophes in proper nouns, suffixes, URLs, code, emoji, normalization, empty input, and encode/decode round trips.
- Version tokenizer and model together. Reject checkpoints whose tokenizer hash or vocabulary size differs.
- Measure bytes/characters/tokens on a held-out Turkish evaluation set; do not choose vocabulary size based on a single sample.

## Workstream C — learning pipeline with rights and privacy gates

The source register currently has no approved sources and the corpus gate is closed. No training job should bypass that gate.

1. Obtain explicit human review for each source's license, redistribution/training permission, privacy risks, attribution requirements, and retention rules.
2. Prefer first-party texts created specifically for MKAOS and public-domain or explicitly permissive materials with documented provenance. A model's license does not automatically clear its training data.
3. Deduplicate exact and near-duplicate documents, remove secrets and personal data, retain source IDs and license metadata, and create deterministic train/validation/test splits.
4. Store an immutable manifest containing source hashes, preprocessing version, tokenizer hash, split IDs, and approval references.
5. Keep evaluation examples out of training. Add Turkish grammar, instruction following, factuality, coding, refusal/safety, and hallucination tests.
6. Train a tiny from-scratch baseline first to validate the pipeline, then scale only after loss curves, checkpoints, and held-out evaluations are reproducible.
7. Publish limitations and provenance; do not claim broad Turkish intelligence from a smoke-test corpus.

## Workstream D — useful capabilities without pretending the base model knows everything

- **Retrieval:** local document search with source snippets and citations; evaluate recall@k and answer faithfulness.
- **Tool use:** explicit typed tool contracts, input validation, permission boundaries, timeouts, and auditable results.
- **Memory:** opt-in local memory with inspect/delete controls and tests that unrelated users cannot see each other's data.
- **Reasoning:** structured task decomposition and verification checks; measure task completion rather than claiming human-like reasoning.
- **Coding:** curated, rights-cleared code tasks, sandboxed tests, and pass@1/pass@k evaluations.
- **Turkish quality:** held-out native Turkish prompts scored for correctness, clarity, grammar, and calibrated uncertainty.
- **Offline operation:** prove network isolation with tests and system-level controls; a Docker network label alone is not an air-gap.

## Release gates

A release must separately report:

- Runtime correctness and benchmark metrics.
- Model/tokenizer/checkpoint compatibility.
- Training data approval status and provenance.
- Held-out quality results with sample counts and evaluation version.
- Offline/network behavior and security test results.

Never report synthetic-weight benchmark speed as pretrained-model performance. Never report reference-model repeatability as MKAOS parity. Never enable training while source approval is closed.
