# MKAOS production release gate

This checklist is an operational gate, not a claim that the deployment has already happened. The repository cannot configure real hosts, issue your organization's certificates, select a licensed model corpus, or migrate private production data without the target environment and owner-controlled inputs.

## 1. mTLS and real network

1. Provision a private CA and per-agent certificates in an approved secret manager. Never commit keys or certificates.
2. Configure the service to require client certificates, trust only the intended client CA, and map each certificate URI SAN to an explicit agent ID allowlist. Reject missing, expired, untrusted, revoked, or unknown identities.
3. Configure TLS 1.3 where supported, short certificate lifetimes, renewal, revocation, audit logs, and key rotation. The preflight's TLS 1.3 capability check only describes the local Python/OpenSSL build.
4. Apply WireGuard routes and host firewall rules on the actual target hosts. Restrict peer routes to the smallest required address ranges; do not expose the service publicly by default.
5. From an authorized client, run the live handshake probe:
   `python -m tools.mkaos_production_preflight --ca /secure/ca.pem --cert /secure/client.pem --key /secure/client-key.pem --probe-url https://your-private-agent.example:8443/health`
   Replace the example endpoint with your real private endpoint. A successful TLS handshake does not verify HTTP authorization, application behavior, firewall completeness, or peer revocation.
6. Independently test negative cases: no client certificate, wrong CA, expired/revoked certificate, unknown URI SAN, and blocked network route. Each must fail closed.

## 2. Live Crypto-RAG data migration

1. Stop writes or establish a documented consistent snapshot; create an encrypted backup and prove it can be restored.
2. Use a separate destination and a fresh, secret-managed AES-GCM key. Never put keys in command history, logs, CI variables printed to output, or Git.
3. Run the repository's migration utility against a disposable copy first. Compare record counts, IDs, payloads, embedding dimensions/model identity, and integrity digests.
4. Test wrong-key rejection, interrupted migration recovery, and restore. Preserve the source until owner approval after verification.
5. Schedule production migration only with an explicit rollback window and a named data owner. The preflight checks path separation; it does not perform or certify a migration.

## 3. Local MKAOS model readiness

1. Obtain a corpus with recorded provenance, license, consent/privacy review, attribution, and redistribution/training permissions.
2. Run training on provisioned hardware with resumable checkpoints and recorded configuration. Do not treat a synthetic CI smoke run as a trained model.
3. Evaluate a fixed, held-out Turkish benchmark for factuality, instruction following, safety, memorization/privacy leakage, and regressions. Publish methodology and results.
4. Package the approved checkpoint locally and set `MKAOS_NATIVE_SHA256` from the verified artifact. Do not silently fall back to third-party inference.
5. Measure TTFT, tokens/second, peak RAM/VRAM, context length, and failure behavior on the actual target hardware. Release only after an independent reviewer signs off.

## 4. Run the read-only preflight

Basic configuration and local artifact checks:

```bash
python -m tools.mkaos_production_preflight --json
```

Include `--model PATH --model-sha256 SHA256` to verify a local checkpoint digest. Include `--ca`, `--cert`, `--key`, and `--probe-url` to attempt a real TLS handshake against a reachable private endpoint. The tool never provisions interfaces, changes firewall rules, migrates data, downloads weights, or trains a model.

## Release decision

Do not mark production-ready until all three independent workstreams—network/mTLS, verified data migration, and model quality—have evidence from the real target environment. A green preflight is necessary but not sufficient. Document test evidence, responsible owner, rollback plan, and remaining risks in the release record.
