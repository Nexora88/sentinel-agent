# MKAOS CPU performance plan

Status: optimization work in progress; no speedup percentage is claimed until a repeatable benchmark is run.

## Changes in the current branch

- The incremental GQA decoder precomputes RoPE sine/cosine tables for the configured sequence window instead of calculating `powf`, `sin`, and `cos` for every generated token.
- The attention decode path reuses one score buffer across query heads, avoiding a heap allocation per head per generated token.
- A unit test compares cached RoPE values with the existing reference implementation over several positions.

These changes target CPU decode overhead. They do not yet make the MKAOS Rust runtime numerically compatible with SmolLM2, and they do not establish a measured tokens-per-second improvement.

## Required benchmark protocol

1. Run `cargo test --release --manifest-path engine/mkaos-inference/Cargo.toml` on a clean checkout.
2. Benchmark the same synthetic checkpoint, prompt token IDs, sequence length, and release build before and after each optimization.
3. Record warm-up count, repetitions, median and p95 latency, prompt prefill time, decode milliseconds/token, tokens/second, peak RSS, CPU model, OS, Rust version, and commit SHA.
4. Run at least 5 measured repetitions after warm-up. Do not compare GitHub-hosted runner timings with the user's PC as if they were the same hardware.
5. Keep a correctness gate: cached vs reference logits and greedy output must match within the existing tolerance before accepting performance results.

## Next bottlenecks to address

- Add a reproducible benchmark harness before attempting further micro-optimizations.
- Replace scalar FP32 matrix multiplication with a tested optimized backend or platform-specific SIMD implementation, preserving a scalar reference path.
- Add weight-only quantization only with accuracy/parity tests and memory measurements.
- Implement and validate a model-specific tokenizer + checkpoint exporter before measuring real pretrained-model generation. The current byte tokenizer (257 IDs) is not compatible with SmolLM2's tokenizer.
- Measure prompt prefill separately from token-by-token decoding; KV caching improves repeated decoding but does not remove the need to process the initial prompt.

## Current limitations

The Hugging Face CPU reference smoke test validates repeatability of the external reference runtime only. It is not a benchmark of the MKAOS Rust runtime and is not a cross-runtime parity test. Model conversion and SmolLM2 numerical parity remain unvalidated.
