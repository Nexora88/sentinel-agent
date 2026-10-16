# MKAOS portability contract (step 1 of 5)

## Goal

MKAOS must be portable across users' machines, not optimized around one developer computer. The first step is an offline host-profile contract that separates what is detected from what has actually been tested.

## Initial support matrix

| Environment | CPU baseline | Accelerator status | Release rule |
|---|---|---|---|
| Linux x86-64 | Candidate baseline | Not probed until an explicit local probe exists | CI + target-device tests |
| Windows x86-64 | Candidate baseline | Not probed | CI + target-device tests |
| macOS x86-64 / Apple Silicon | Candidate baseline | Metal not assumed from OS/CPU name | CI + exact-device tests |
| Linux ARM64 | Python metadata expected to be portable; native Rust build still must be tested | Not probed | ARM64 CI/device test |
| Windows ARM64 / other architectures | Not yet certified | Not probed | Add explicit CI/device evidence |

The core.platform_profile.get_platform_profile() function is intentionally metadata-only and network-free. It normalizes OS/architecture identifiers and reports Python runtime identity. It does not claim that a model, Rust binary, GPU kernel, quantization format, or package is compatible with the host.

## Portable runtime design

1. Keep a correct CPU path as the fallback; accelerator paths are optional adapters.
2. Detect hardware capabilities only with explicit local probes, then benchmark them.
3. Keep model files and tokenizer formats versioned and hash-verified.
4. Do not require CUDA, ROCm, Metal, Docker, or an internet connection for the basic metadata/profile path.
5. Treat missing acceleration as a performance limitation, not as a correctness failure.
6. Publish separate install/build instructions for Windows, Linux, and macOS.
7. Compare outputs against reference tests within documented numerical tolerances.

## Acceptance gates

- Unit tests pass on Windows, macOS, and Linux CI.
- Rust crate builds and inference tests pass on each OS/architecture advertised as supported.
- A real local checkpoint loads and generates on each advertised runtime.
- Per-device latency (p50/p95), tokens/s, peak RAM/VRAM, startup time, and long-run stability are measured on the same benchmark prompts.
- Accelerator support remains not_probed until an actual device test provides evidence.
- No telemetry or network call is introduced by host profiling.

## Independence roadmap

1. **Portability contract and baseline tests** — this change; host identity is separated from unverified accelerator/model claims.
2. **Source and dataset sovereignty** — local source archive hashes, rights/attribution review, privacy screening, and an approved corpus manifest.
3. **Owned tokenizer and from-scratch training** — reproducible training from random initialization with held-out Turkish validation and checkpoint hashes.
4. **Native runtime parity and performance** — checkpoint round-trip, fuzz/property tests, Python/Rust parity, memory/latency/token-throughput benchmarks, CPU SIMD and optional vendor-specific accelerator adapters.
5. **Independent release audit and rollout** — license/dependency audit, offline test, security and Turkish-quality evaluation, staged cutover, rollback rehearsal.

## Current limitations

This step does not train model weights and does not certify MKAOS as fully independent. The repository's current source register has no approved training sources, so a real training run must remain blocked. Cross-platform Python CI alone is not proof that the Rust inference engine or a trained model works on every device.
