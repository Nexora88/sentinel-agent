# MKAOS Reasoning, Mesh, Hardware and Sovereignty Plan

## What this change implements now

- core.reasoning_engine: a bounded local-model draft -> critique -> synthesis flow, optionally using distinct local models for each role. It returns concise summaries and uncertainty, not private chain-of-thought. It cannot execute tools, mutate files, or merge patches.
- core.hardware_backends: a capability registry that explicitly marks CUDA, ROCm, Metal, Gaudi and NPU/TPU as unprobed until a device-specific check is supplied. A probe passing is not a benchmark or production certification.
- core.agent_mesh: Ed25519-signed, short-lived, size-limited, replay-checked JSON task envelopes. The task allowlist contains only status, research_summary, code_review, test_request and plan. Shell/code execution payloads are rejected.
- scripts/benchmark_local_reasoning.py: runs the existing Turkish quality prompt set against local Ollama and records latency and raw responses for manual evaluation.
- deploy/kubernetes: a restricted, single-replica cluster deployment scaffold with a non-root pod, read-only root filesystem, secret references, internal ClusterIP service, persistent memory claim and default-deny-style network policy.

These are concrete foundations, not a claim that MKAOS already has a trained proprietary model, a complete P2P runtime, a high-availability distributed data plane, or every hardware backend working.

## Dedicated MKAOS model family and MoE

A genuine MKAOS-LLM requires a legally reviewed dataset, provenance/license records, deduplication, PII and secret removal, training/validation/test splits, compute budget, fine-tuning runs, model cards, quantization, red-team evaluations and reproducible releases. Do not train on live zero-day exploit instructions or private customer code without authorization. Build an evaluation baseline before fine-tuning.

A mixture-of-experts model is a trained architecture with expert sub-networks and a learned router; selecting different local Ollama models for draft, critique and synthesis is role-based model routing, not MoE. The existing router can serve as a baseline. Benchmark it against the new multi-pass reasoning flow and report task accuracy, latency, peak RAM/VRAM, refusal quality and regression rate. Never report a benchmark result without the exact model digest, quantization, device, dataset revision and command.

## Cluster orchestration and private agent mesh

The Kubernetes manifests intentionally deploy one replica. Before horizontal scaling, move sessions, WebAuthn challenges, idempotency, approval records, job state and encrypted storage to services designed for concurrent access. Add quotas, leases, cancellation, health-based scheduling, audit trails and tenant isolation.

The signed task envelope provides message integrity/authenticity only. It does not encrypt traffic. A real inter-office mesh needs peer identity enrollment, mutual TLS, key rotation/revocation, replay protection, network segmentation, explicit peer allowlists and an operator-controlled enrollment process. Do not enable open peer discovery or remote code execution by default. The first supported messages should remain data-only plans, summaries, test requests and code-review requests.

## Hardware portability

Keep Ollama/llama.cpp as the portable baseline. Add CUDA, ROCm, Metal, Gaudi or NPU-specific adapters only behind optional dependencies and device tests. vLLM is useful for compatible accelerator/server configurations, but is not a universal local runtime and does not make CPU, Apple, AMD and all NPUs equivalent. Measure tokens/second, time-to-first-token, peak memory, concurrency, power/thermal throttling and output correctness on actual devices. Mark unsupported/unmeasured hardware as unknown.

## Zero-knowledge, FHE and privacy

FHE can evaluate selected computations over ciphertext under substantial scheme and performance constraints; it is not a drop-in way to hide arbitrary search intent from ordinary search engines while still receiving ordinary search results. This PR does not implement FHE. Prefer local retrieval, local query redaction, allowlisted endpoints, minimum necessary outbound data, egress denial by default, and auditable explicit consent. Research FHE/PIR only for a narrowly defined operation with a threat model and measured latency/cost.

## Governance and open-source maturity

ISO 27001, SOC 2 and Common Criteria require organizational controls, evidence, independent assessment and ongoing operations; passing CI is not certification. Build toward them with threat models, asset inventory, dependency/SBOM tracking, signed releases, vulnerability disclosure, incident response, backup restore drills, access reviews and an external penetration test.

Community growth should be earned through contribution guidelines, code of conduct, issue templates, reproducible development setup, small reviewable PRs, public benchmarks and clear licensing/provenance. Do not claim a contributor community or national ownership for upstream model weights without evidence.

## Validation checklist

- [ ] CI passes on the exact PR head.
- [ ] Unit tests verify signed messages, replay rejection, task allowlist and bounded reasoning.
- [ ] Kubernetes YAML is parsed and reviewed against the actual cluster's CNI, storage and ingress.
- [ ] Image is built as non-root and tested with read-only root filesystem.
- [ ] Two-node mTLS tests, key rotation and revocation are exercised before enabling mesh transport.
- [ ] Hardware support is claimed only after reproducible device tests.
- [ ] Fine-tuned model results are compared with the baseline on a held-out Turkish task set.
- [ ] Host-level egress and encrypted backup/restore are tested independently of application CI.
