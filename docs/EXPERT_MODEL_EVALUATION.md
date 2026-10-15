# MKAOS model evaluation and deployment gates

This document separates automated diagnostics from evidence that requires humans or real infrastructure. No model ranking, two-city network validation, certification, or FHE capability is claimed by this repository.

## 1. Reproducible local Ollama baseline

Run on a machine with Ollama installed and the models downloaded:

```bash
ollama pull qwen2.5:7b
ollama pull deepseek-coder:6.7b
python scripts/evaluate_turkish_models.py --models qwen2.5:7b,deepseek-coder:6.7b --output memory/benchmarks/baseline.json
```

Use the exact model tags, hardware, OS, Ollama version, quantization, context settings, dataset SHA-256, and run date in any report. Repeat runs after a cold start and a warm start. The script records per-task latency, token counts where Ollama provides them, output hashes, lexical diagnostics, and Ollama-reported model size/VRAM observations where available. The latter are **not** peak host RAM measurements or a complete GPU memory profile. Collect OS-level peak RAM/VRAM separately for comparable hardware-level rankings.

The script deliberately blocks non-local model endpoints. Do not put secrets or sensitive data in the public benchmark.

## 2. Expert scoring protocol

1. Freeze the dataset and record its SHA-256 before testing.
2. Randomize model aliases independently of model names; reviewers must not see which model produced an answer.
3. Use at least two independent reviewers for each answer. Adjudicate disagreements on critical security failures.
4. Score each dimension from 1 to 5: factual correctness, task completion, security/safety, reasoning/evidence, and Turkish clarity.
5. Record critical security failures separately; never average them away into a high overall score.
6. Preserve exact prompt, model tag, generation settings, raw output hash, reviewer rubric, and adjudication notes.
7. Keep development/tuning data separate from a frozen holdout set. Do not use holdout examples for prompt tuning or fine-tuning. Rotate or privately retain future holdout items if benchmark leakage is a concern.

Use `benchmarks/expert_review_template.json` for each blinded review. It is an empty schema, not an evaluation result. Do not publish a ranking until the completed reviews, hardware details, repeated runs, and failure analysis are available.

## 3. Two-node Istanbul–Ankara acceptance gate

The repository currently contains TLS context helpers and signed-envelope verification; these do not constitute a running transport or prove a two-node deployment. Before claiming readiness, deploy two independently administered hosts and record:

- CA chain, unique node certificates, SAN/hostname validation, mutual TLS, and certificate expiry checks.
- Revocation mechanism and proof that a revoked certificate is rejected on both nodes (for example, CRL/OCSP or a tightly controlled short-lived certificate rotation procedure). The current local peer denylist is not a PKI revocation system.
- Concurrent delivery of the same signed task to both nodes; exactly one durable claim must succeed.
- Process restart and host restart with replay history preserved.
- Packet loss, latency, disconnect, reconnect, clock skew, and unavailable shared-store tests.
- Negative tests for wrong audience, expired messages, unknown signer, altered signature, oversized payload, and data-only policy violations.
- Logs that contain correlation IDs but not secrets or full sensitive payloads.

Do not describe the mesh as operational until these tests have passed against the actual network transport and shared datastore.

## 4. Shared state, backup and disaster recovery

The current SQLite replay store is intended for one host and is not a multi-node consensus or shared-state layer. A production design needs a shared transactional database with unique constraints for replay claims, tenant-scoped session state, approval state transitions, audit events, least-privilege roles, TLS, migrations, connection limits, and defined consistency semantics.

Before production use, test automated backups, encrypted off-site copies, restore into a clean environment, integrity checks, recovery-point objective (RPO), recovery-time objective (RTO), and failover while requests are in flight. Record measured RPO/RTO rather than estimates. A passing unit test is not a disaster-recovery test.

## 5. Fine-tuning, FHE, and certifications

Fine-tuning requires rights-cleared, privacy-reviewed training data; a documented data lineage and deletion process; a frozen, separate holdout set; reproducible training configs; and post-training safety and regression evaluation. No proprietary MKAOS-trained model is included by this evaluation harness.

No FHE implementation is provided by this change. FHE requires a separately selected scheme/library, threat model, parameter review, correctness/performance tests, and careful disclosure of which computations are actually encrypted. Do not infer FHE from TLS, encryption at rest, or signed messages.

ISO 27001, SOC 2, and Common Criteria are not software flags. Any claim requires a defined scope, evidence, independent assessment and, where applicable, a formal certification/audit. This repository does not claim these attestations.
