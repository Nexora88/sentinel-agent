# MKAOS Evaluation Baseline and Mesh Hardening

## Turkish coding/security baseline

The synthetic, versioned seed dataset is `benchmarks/turkish_coding_security.json`. It covers Turkish Python coding, error handling, safe output, secret exposure response, path validation, signature-versus-confidentiality, and prompt-injection resistance. It is not a representative benchmark or certification.

Run comparisons against models already installed in local Ollama:

```bash
ollama pull qwen2.5:7b
ollama pull deepseek-coder:6.7b
python scripts/evaluate_turkish_models.py --models qwen2.5:7b,deepseek-coder:6.7b --output memory/benchmarks/baseline.json
```

The runner blocks remote endpoints and records dataset SHA-256, per-task latency, token counts when available, output hashes, outputs and transparent lexical checks. Keyword coverage is not correctness. Manually score answers with a fixed rubric; record exact model digest, quantization, hardware, RAM/VRAM, repeat count, pass rate, severity-weighted security defects, refusal precision/recall, latency percentiles and regression rate. Do not include private customer prompts, credentials or production logs. Keep benchmark outputs local unless reviewed.

Before fine-tuning, collect licensed/consented examples, remove personal data and secrets, deduplicate, split train/dev/test by source and near-duplicate group, and freeze a held-out test set. A true MoE requires trained expert subnetworks and a learned router; selecting separate models for roles is not MoE.

## Mutual TLS and durable replay

`core.mesh_tls` creates TLS client/server contexts with CA validation, client certificates, client hostname checks and TLS 1.2 minimum. It does not start a listener, issue certificates, enroll peers, rotate/revoke PKI certificates or prove a live İstanbul–Ankara connection.

`core.mesh_replay.DurableMeshVerifier` adds peer-ID denylisting and an atomic SQLite task-ID claim that persists across process restarts. Configure a durable path on the host. SQLite is a single-host baseline, not a shared multi-host replay database; for replicas use a shared transactional store with uniqueness constraints and test backup/restore. A local denylist is not a PKI certificate revocation service.

Signed JSON provides no confidentiality. Do not send secrets in task envelopes; protect transport with mTLS and limit peer allowlists. Unit tests validate local policy logic only. A release candidate still needs two real nodes, separate certificates, untrusted/expired/revoked certificate rejection, replay after restart, concurrent duplicate delivery, clock skew, partition/recovery, backup restore and audit-log review.

No ISO 27001, SOC 2, Common Criteria or independent security certification is implied.
