# MKAOS Production Readiness Runbook

**Status: implementation and operator-controlled deployment are separate.** This runbook does not claim that a live mesh, production mTLS, a user-data migration, or an approved MKAOS-trained model has been provisioned.

## 1. Run the fail-closed preflight

From the repository root:

```bash
python tools/mkaos_production_preflight.py --json
python tools/mkaos_production_preflight.py --require-network-config --json
python tools/mkaos_production_preflight.py --ca /secure/path/clients-ca.pem --cert /secure/path/service-cert.pem --key /secure/path/service-key.pem --require-network-config --json
```

The script checks configuration presence and local file/hash properties only. It does not make network calls, validate a live TLS handshake, provision a firewall, issue/revoke certificates, migrate a database, or benchmark a model. Never put private keys in the repository or CI logs.

## 2. Production mTLS and network

Before enabling public traffic, an operator must complete all of these in the actual deployment environment:

- Assign a domain and terminate HTTPS at a maintained reverse proxy or supported ingress. Enforce TLS 1.3 where all clients support it; explicitly document any compatibility exception.
- Issue service and client certificates from a private CA; verify certificate SAN/URI identity against an explicit agent allowlist. Keep private keys in a secret manager or OS-protected path with least-privilege permissions.
- Configure client-certificate verification as mandatory (not optional), test a valid client and negative cases (missing cert, untrusted CA, expired cert, wrong SAN/URI, revoked fingerprint).
- Define certificate rotation, emergency revocation, CA rotation, clock synchronization, audit retention and an on-call owner. A helper function or environment variable is not an mTLS listener.
- Apply host/cloud firewall rules and egress allowlists; expose only required ports. Verify from a second machine that unintended ports are unreachable. WireGuard requires real peer keys, addresses, routes, firewall policy and a tested rollback plan.
- Run an authorized integration test from the deployed network and retain redacted evidence. A successful unit test is not evidence of a live secure network.

Do not place real production keys in a pull request. The repository alone cannot create cloud firewall rules, DNS records, certificates, VPN peers or secret-manager entries.

## 3. Existing-data migration

Use a maintenance window and a separate destination. Before switching readers:

1. Stop writes or establish a consistent snapshot of the source.
2. Create a protected backup and prove it can be restored to a disposable location.
3. Run the repository migration command documented for the selected backend against a copy first.
4. Compare source/destination record counts, stable IDs, metadata, text, vector dimensions, embedding model/version, and integrity hashes. Check duplicate and failed-record reports.
5. Run application-level retrieval tests against the destination and record expected/actual results.
6. Switch readers only after owner approval. Keep the source and verified backup through the rollback window; do not delete plaintext data automatically.
7. Record the operator, timestamp, source/destination identifiers (not secrets), counts and verification report.

This preflight intentionally does not run migration or touch the user's data. Do not migrate live data from CI.

## 4. Local model acceptance gate

A third-party checkpoint running locally is not an MKAOS-owned trained model. Before calling a model production-ready:

- Approve and record dataset provenance, license, consent/permission, privacy/PII review and train/validation/test split. The test set must not be used for optimization.
- Provision the checkpoint locally from an immutable source revision, record SHA-256 hashes, model/tokenizer configuration, license, quantization and dependency versions.
- Verify the intended Rust/native runtime actually loads the checkpoint and tokenizer. Run repeated inference, malformed/oversized prompt tests, context-limit tests, and a no-network test.
- Evaluate on a versioned, held-out Turkish suite with human-reviewed scoring for factuality, instruction following, refusal behavior, reasoning, spelling and robustness. Publish the test-set version, sample count, rubric, scores and limitations.
- Benchmark on the actual target hardware: peak RAM/VRAM, startup time, time-to-first-token, tokens/sec, concurrency and long-context behavior. Define release thresholds before measuring.
- Compare a known baseline and retain raw, non-sensitive metrics. A small synthetic CI smoke test is not Turkish quality evidence.
- For an MKAOS-trained model specifically, train only after approved data and compute are available, preserve reproducible training metadata, and independently evaluate the final checkpoint.

If the approved source registry is empty or the target machine/data/compute is unavailable, the honest state is **blocked**, not production-ready. This repository change cannot supply compute, grant dataset rights, or run training on the operator's hardware.

## 5. Release gates and rollback

A production release requires all gates to have evidence:

- [ ] unit and integration tests pass on the exact release commit
- [ ] dependency and secret scans reviewed; no unresolved critical/high finding without a documented exception
- [ ] live mTLS negative and positive handshake tests pass
- [ ] firewall/egress tests pass from the deployed environment
- [ ] migration restore, count, content and retrieval checks pass
- [ ] model provenance, checksum, runtime compatibility, held-out Turkish evaluation and hardware benchmark reviewed
- [ ] health/metrics, logs with secret/PII redaction, backups, alerting and rollback procedure tested
- [ ] deployment owner explicitly approves production enablement

If any gate is unverified, do not label the system production-ready. Keep integrations disabled or private until the operator supplies required infrastructure and evidence.

## 6. Evidence capture

Attach sanitized command output and test reports to the release record. Never attach tokens, private keys, raw user data, full environment dumps, or unredacted logs. This runbook is a checklist and preflight aid—not a certificate, security audit, or proof that deployment has occurred.
