# MKAOS productization gates: operator-ready, not marketing-ready

This document separates work that can be automated safely from claims that require evidence. It is a defensive, local-first agent platform; it must not be marketed or built as an offensive cyber weapon.

## 1. One-command setup

Use `scripts/mkaos_bootstrap.sh` on Linux/macOS with Python 3.11+, Docker Compose v2, and curl. It creates a private `.env`, generates a strong first-run `OWNER_PASSWORD` only when blank, validates Compose, builds the web image, starts the service, and checks health. It never prints a password already supplied by the operator.

Optional model downloads require an interactive opt-in and `config/model-assets.lock`. Every entry must pin an HTTPS URL, SHA-256, and destination beneath `models/`; there are deliberately no fabricated/default model hashes. A matching digest proves bytes match the lock, not license rights, provenance, safety, or quality. Review the upstream license and distribution terms before creating a lock entry. Keep model files out of Git.

- Preflight only: `scripts/mkaos_bootstrap.sh --no-start`
- Start the app: `scripts/mkaos_bootstrap.sh`
- Explicitly opt in to locked model downloads: `scripts/mkaos_bootstrap.sh --download-assets`

Windows users should use WSL2 with Docker Desktop until a native PowerShell bootstrap receives equivalent tests.

## 2. Data and training: no shortcuts

A public URL, checksum, or successful parser run does not grant training or weight redistribution permission. Before a real training run, the dataset manifest must identify the exact source/version, terms, permitted purpose, privacy review, source archive digest, cleaned corpus digest, split strategy, and an accountable human review. Keep test documents out of optimizer/model-selection loops. A billion-token target is a planning target, not a reason to skip rights review or ingest a source wholesale. The current small smoke checkpoint is not a useful Turkish LLM.

## 3. Hardware and 1B–3B planning

CUDA/ROCm training acceleration is available only when a compatible PyTorch build and actual device are present. The Rust inference engine remains CPU-only until a backend is implemented and tested against the CPU reference. Do not report GPU support from adapter names or environment detection alone.

The current byte-tokenized trainer is a research harness, not an efficient 1B–3B training recipe. Before scale-up: choose and validate a subword tokenizer, run a licensed-data pilot, profile tokens/sec and validation quality, estimate optimizer/activation/checkpoint storage, implement resumable checkpoints, and test deterministic restore. 1B–3B weights alone are not the full memory budget; optimizer states, gradients, activations, context length, and checkpoint copies matter.

## 4. Retrieval: semantic means measured, not named

- `mkaos-native` is a deterministic lexical/hash baseline.
- `local-semantic` can use an already-installed Sentence-Transformers model with local-only loading and remote code disabled.
- Ollama embeddings remain opt-in compatibility only.

Before promoting a local semantic model, record an immutable SHA-256 file inventory, review its license and privacy implications, pin its exact model version, and run a Turkish retrieval benchmark containing paraphrases, inflections, spelling variants, code/CVE queries, hard negatives, and relevance judgments. Report Recall@k, MRR/nDCG, latency p50/p95, memory, and cold-start time. There is no honest basis for claiming 100% semantic quality.

A Rust transformer sentence encoder is a separate implementation milestone: it needs a defined tokenizer, model format, tensor operations, pooling/normalization, numerical parity tests, and licensed weights. The current Rust decoder does not become a semantic embedding encoder merely because it has Transformer operations.

## 5. Kubernetes and shared state: do not scale unsafe state

The current deployment is single-replica by design. The local PVC and process-local session/WebAuthn challenge state are not a distributed data plane. Increasing replicas now can cause login, challenge, approval, idempotency, and memory consistency failures.

Required gates before enabling multiple replicas:
1. Inventory all session, WebAuthn challenge, approval/replay, job-idempotency, tenant memory, and audit state with explicit TTL and deletion semantics.
2. Select PostgreSQL as the durable source of truth for sessions/challenges/approvals/audit and job state; use Redis only for cache/short-lived coordination, never as the sole audit record. Use TLS/mTLS, least-privilege credentials, encryption at rest, network policies, backup/restore and key rotation.
3. Implement migrations, unique constraints, transaction boundaries, tenant isolation, challenge single-use semantics, idempotency keys, and rolling-upgrade compatibility.
4. Add multi-replica integration tests: simultaneous login/challenge verification, duplicate approvals, retries, node loss, database failover, restore, and cross-tenant isolation.
5. Only then set replicas > 1 and publish measured p95 latency, error rate, recovery time, and tested capacity.

Until these pass, keep `replicas: 1`. A Redis/PostgreSQL URL alone does not make an application stateless.

## 6. Enterprise release gates

- Threat model, abuse cases, security contact, vulnerability response, SBOM, dependency pinning, signed provenance, reproducible build and release artifact hashes.
- Secrets never committed; first-run secrets displayed once, stored with restrictive permissions, and rotated.
- Offline claim backed by host-level egress-deny tests and packet capture, not a UI badge.
- Accessibility, installation/uninstallation, upgrade/rollback, backup/restore and migration docs tested by a clean-machine operator.
- Support matrix names exact OS, CPU/GPU, driver, model/checkpoint digest and tested workload.
- Public claims limited to what the latest CI, security review, independent Turkish quality set, and deployment tests actually prove.
