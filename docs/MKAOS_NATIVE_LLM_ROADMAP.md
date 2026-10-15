# MKAOS Native LLM — engineering roadmap

## Goal
Move inference away from the Ollama service behind a MKAOS-owned Rust runtime, with a reviewed model bundle format, local-only defaults, reproducible benchmarks, and explicit release gates. This first slice is a foundation, not a production transformer runtime.

## Implemented in this change
- A dependency-free Rust crate (mkaos-llm-core) with unsafe Rust forbidden.
- Checked CPU tensor primitives: matrix multiplication, stable row-wise softmax, RMSNorm, SiLU, and embedding lookup.
- A bounded greedy autoregressive decode loop behind tokenizer and backend traits.
- Versioned model-manifest validation for dimensions, context limits, stop token, relative weight path, and digest syntax.
- Rust unit tests and a dedicated CI workflow.

## Not implemented yet — do not claim otherwise
- A production transformer architecture/forward pass, tokenizer implementation, or compatible trained weights.
- Actual SHA-256 verification of weight files, signature verification, or a model-bundle installer.
- CUDA, ROCm, Metal, Vulkan, NPU/TPU, quantization, KV cache, batching, streaming, or peak RAM/VRAM instrumentation.
- Training/fine-tuning MKAOS model weights, measured model rankings, or a demonstrated advantage over larger models.
- Migration of the Python application away from core/ollama_client.py.

The weights_sha256 field is currently format-validated only. It is not proof that a weight file matches the manifest. Do not load untrusted bundles based on this manifest alone.

## Staged implementation plan
1. Runtime core: implement and test transformer blocks, rotary position embeddings, attention masking, KV cache, and deterministic decoding.
2. Bundle integrity: define canonical manifest serialization; verify every weight shard against SHA-256 and a locally trusted signature before loading. Reject path traversal and oversized dimensions before allocation.
3. Tokenizer and format: implement a documented tokenizer/model format with golden vectors and compatibility tests. Importing existing weights requires license and format checks; this is not equivalent to training a native MKAOS model.
4. CPU reference backend: run a small test model end-to-end on CPU with reproducible logits and golden tests.
5. Hardware backends: add CPU SIMD first; treat CUDA/ROCm/Metal and domestic NPU/TPU targets as separately reviewed adapters with parity tests. Do not claim support before device tests.
6. Python integration: introduce a MKAOS-native provider interface and route existing calls through it only after parity tests. During migration keep an explicit compatibility mode; native mode must fail closed instead of silently using cloud endpoints.
7. Training and controlled learning: use licensed and privacy-reviewed Turkish coding/security datasets; preserve source-level splits; train/fine-tune offline; evaluate held-out benchmarks and critical safety regressions; require human release approval.
8. Deployment and scaling: measure p50/p95 latency, throughput, peak host RAM, GPU VRAM, power where measurable, concurrent sessions, restart recovery, and two-node network behaviour on actual hardware.

## Sovereignty and security definition
Locally hosted is not the same as fully sovereign. Sovereignty requires source/build provenance, dependency inventory, reproducible builds, signed artifacts, verified weights, no unapproved egress, hardware/driver documentation, independent security review, and operational tests. Rust memory safety does not eliminate logic bugs, unsafe code in dependencies, supply-chain risks, or zero-day vulnerabilities.

## Current status
This repository still uses Ollama in the application path. This Rust crate does not run a production LLM and must not be marketed as an operational Ollama replacement. The migration should proceed in small pull requests with CI and hardware evidence.
