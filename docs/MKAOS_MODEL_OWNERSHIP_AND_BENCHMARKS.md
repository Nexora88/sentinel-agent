# MKAOS: Model Ownership, Validation and Performance Gates

> Status: engineering plan and release gates, not a claim that a trained MKAOS model or device benchmark already exists.

## Ownership boundary

MKAOS is not an independently trained language model until all of the following are true:

1. The tokenizer implementation and its versioned vocabulary/merges (if applicable) are authored and tested by this project.
2. The model configuration and forward pass agree on token IDs, tensor shapes, normalization, positional encoding, attention, cache layout, and output head.
3. A reproducible training run produces MKAOS-owned weights from a documented initialization and an auditable dataset.
4. A clean checkpoint can be loaded by the Rust inference engine without silently substituting another model or calling a hosted/Ollama runtime.
5. Held-out evaluation demonstrates useful quality, and performance is measured on identified hardware.

Until then, describe SmolLM2-135M-Instruct as a third-party test checkpoint, any synthetic decoder as a smoke-test component, and the Rust engine as experimental. Do not describe these as a trained sovereign model.

## Staged delivery

### Gate A — Reproducible baseline

- Pin the source revision, compiler/toolchain, model config, tokenizer revision, dataset manifest, and random seeds.
- Run correctness tests before timing: tokenizer round-trip and Unicode/Turkish cases; checkpoint/config compatibility; deterministic small-input forward pass; logits finite checks; generation termination and context-limit checks.
- Keep synthetic unit tests separate from real-checkpoint tests. Never use synthetic tests as evidence of language quality.

### Gate B — Data governance

- Accept only records with documented origin, license/permission basis, collection date, and content hash.
- Reject records with unknown rights, malformed encoding, duplicates, or disallowed personal data.
- Split by source/document before chunking to prevent train/validation/test leakage.
- Keep the test split untouched until final evaluation. Publish counts, hashes, filtering reasons, and license notes, not private raw text.
- Human review is required; a manifest is evidence of process, not legal advice or proof that every source is lawful.

### Gate C — Tokenizer and architecture

- Define a versioned tokenizer contract: vocabulary size, special-token IDs, normalization policy, encode/decode behavior, and compatibility metadata.
- Test Turkish characters (ç, ğ, ı, İ, ö, ş, ü), punctuation, whitespace, emoji, long inputs, empty inputs, and malformed UTF-8 handling.
- Implement and independently test the actual architecture before training: embeddings, causal mask, positional encoding (including RoPE if configured), attention, MLP, residuals, normalization, tied/untied output head, and cache behavior.
- Add a checkpoint manifest containing architecture ID/version, tokenizer hash, tensor names/shapes/dtypes, quantization, and weight-file hashes. Loading must fail closed on mismatches.

### Gate D — Train MKAOS-owned weights

- Begin with a small randomly initialized model to validate the complete train-save-load-generate loop.
- Record config, optimizer/scheduler, seed, tokens seen, training/validation loss, elapsed time, hardware, peak RAM/VRAM, and artifact hashes.
- Stop or investigate when validation loss diverges or data leakage is detected.
- Only after this works should model size and dataset size grow. More parameters alone do not guarantee better Turkish quality.

### Gate E — Remove temporary external runtime paths

- Introduce a native Rust embedding interface and a versioned local embedding artifact produced by the project, or a transparent lexical/sparse retrieval fallback while training is unavailable.
- Keep Ollama behind an explicitly optional development adapter during migration; production/offline mode must not silently call it.
- Add tests with Ollama unavailable and network access disabled. Assert that startup, memory retrieval, and chat either work locally or return an explicit capability error.
- Remove SmolLM2 from the default path only when a compatible MKAOS checkpoint passes the correctness and quality gates. Do not replace a known external dependency with random or untrained weights and call it an improvement.

## Benchmark protocol (TTFT comes last)

Use the same physical device, power mode, build flags, context, prompt set, generation limit, and warm-up policy for every comparison. Record CPU/GPU model, RAM/VRAM, OS, Rust version, commit SHA, checkpoint/tokenizer hashes, and whether the run is offline.

Measure separately:

- **Retrieval latency:** cold and warm p50/p95, index size, corpus size, Recall@1/3/5, MRR@10 and nDCG@10 on a fixed, held-out query set.
- **Generation throughput:** prompt tokens/s and generated tokens/s; report prompt and output token counts, with multiple repetitions and p50/p95.
- **Memory:** idle and peak resident RAM; GPU allocated/peak VRAM when applicable.
- **Quality:** held-out Turkish tasks, factuality checks, instruction following, repetition rate, and human-reviewed samples. Speed is not a substitute for quality.
- **TTFT:** only after tokenizer, checkpoint compatibility, output correctness, and stable throughput tests pass. Define TTFT consistently as request start to first generated token; report cold-start and warmed results separately.

Never publish a single best run as a benchmark. Report median, p95, sample count, failures, hardware and exact command. Do not claim a result until it has actually been run.

## Acceptance checklist

- [ ] No silent third-party model fallback in offline mode.
- [ ] Tokenizer/checkpoint hashes match and mismatch tests fail closed.
- [ ] Native Rust generation passes deterministic and edge-case tests.
- [ ] Dataset manifest and source-level split checks pass.
- [ ] MKAOS-owned weights are produced by a reproducible training run.
- [ ] Ollama-disabled and network-isolated tests pass.
- [ ] Quality and memory baselines are published before TTFT.
- [ ] TTFT is measured last on the same identified physical device.
