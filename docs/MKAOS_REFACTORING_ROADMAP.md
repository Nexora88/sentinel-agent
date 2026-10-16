# MKAOS Refactoring & Independence Roadmap

This roadmap tracks engineering work as evidence-gated milestones. A completed code path is not evidence of a trained model, semantic quality, air-gap isolation, or production scalability.

## Milestone A — First-run UX and operational clarity

- [x] One-command Docker bootstrap with an explicit offline mode.
- [x] Generate a strong owner secret once, store it in a private local `.env`, and show it only in the local terminal.
- [x] Add a model readiness endpoint that does not expose local paths or model hashes.
- [x] Replace the default missing-checkpoint HTTP 503 UX with an explicit `setup_required` chat message; do not call it model-generated text and do not use third-party fallback.
- [ ] Test bootstrap on Windows PowerShell separately; the current script targets POSIX shells.
- [ ] Add a signed/checksummed offline bundle manifest and reproducible dependency lock.

## Milestone B — A real independent Turkish model

- [ ] Approve each corpus source, license, redistribution rights, privacy policy, and deduplication policy.
- [ ] Build a documented, reproducible corpus manifest with source hashes and exclusion records.
- [ ] Establish tokenizer training and Unicode/Turkish normalization tests.
- [ ] Train from random initialization only on approved data; record seed, configuration, data manifest hash, compute budget, and checkpoints.
- [ ] Publish validation curves and memorization/privacy checks.
- [ ] Validate the produced checkpoint format, tensor shapes, hash, tokenizer compatibility, and loadability in the Rust engine.
- [ ] Evaluate against a frozen Turkish set: language quality, factuality, arithmetic, multi-step reasoning, coding, safety, latency, and RAM. Report baselines and confidence intervals.

**No claim of a completed independent model is allowed until a real checkpoint is produced, loaded, and evaluated.** Synthetic CI fixtures only prove code plumbing.

## Milestone C — Semantic retrieval, still fully local

- [ ] Define a small, license-cleared Turkish query/document relevance dataset.
- [ ] Measure the current hashed n-gram baseline and hybrid lexical reranker (Recall@k, MRR/nDCG, latency, RAM).
- [ ] Train a small embedding model from approved data or implement a fully documented from-scratch objective; do not relabel hash features as semantic embeddings.
- [ ] Add a local embedding runtime, model/tokenizer hashes, bounded batches, tenant isolation, and migration/versioning for vector collections.
- [ ] Compare hybrid lexical + semantic retrieval to the baseline before changing defaults.

## Milestone D — Stateful single node first, then distributed deployments

- [ ] Introduce a storage interface for sessions, WebAuthn challenges, chat history, approvals, and agent memory.
- [ ] Keep SQLite/local encrypted storage as the simple single-node option; add PostgreSQL for shared durable records and Redis only for ephemeral session/challenge/queue coordination where justified.
- [ ] Define migrations, transaction boundaries, retention/deletion, backup/restore, tenant isolation, and key rotation.
- [ ] Add multi-worker integration tests proving login, passkeys, chat history, and approvals work across replicas.
- [ ] Only then publish Kubernetes multi-replica deployment manifests. PVC-backed per-pod files are not a shared state layer.

## Milestone E — Streaming and agent capabilities

- [ ] Add an authenticated streaming chat contract (SSE) with request IDs, cancellation, timeouts, bounded output, and backpressure.
- [ ] Keep normal JSON chat as a compatibility path.
- [ ] Add a permissioned tool registry: read-only by default; explicit user approval for file writes, code execution, network actions, or device control.
- [ ] Execute untrusted code only in a disposable sandbox with CPU/memory/time limits, no ambient credentials, and network disabled by default.
- [ ] Add audit events and adversarial tests for prompt injection, tenant crossing, SSRF, command injection, and cancellation.

## Milestone F — Verifiable offline supply chain

- [ ] Separate build-time downloads from runtime; vendor/pin dependencies and image digests.
- [ ] Generate SBOM, license report, source register, and artifact hashes.
- [ ] Provide a signed offline bundle with model files separately licensed and explicitly supplied.
- [ ] Verify runtime egress with host firewall/network namespace tests, not environment flags alone.
- [ ] Test on clean machines with no network and no pre-populated caches.

## Current truth

The repository does **not** yet contain a reviewed, independently trained, useful Turkish MKAOS checkpoint. The native hashing embedding baseline is not semantic embedding. The current file-backed session and memory paths are not multi-replica stateless storage. The bootstrap script reduces setup friction but does not make a missing model appear or download unreviewed weights. These are deliberate evidence gates, not completed capabilities.
