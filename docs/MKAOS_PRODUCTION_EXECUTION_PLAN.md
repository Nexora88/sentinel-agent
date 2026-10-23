# MKAOS Production Execution Plan

> Status: **operator-run acceptance plan; not evidence of a deployed production system.**
>
> This repository cannot configure machines, issue/revoke real certificates, access private data stores, or train/benchmark a model unless an authorized operator supplies the target environment, reviewed inputs, and credentials. Never commit private keys, customer data, production exports, or model weights.

This plan converts the remaining production gaps into observable acceptance gates. A checklist item is complete only when its evidence is attached to a reviewed release record.

## 0. Release policy

- [ ] Name a technical owner and security reviewer for the deployment.
- [ ] Inventory hosts, OS versions, network ranges, data owners, data classification, model license and hardware.
- [ ] Keep production credentials outside GitHub and repository files; use a secret manager or host secret store.
- [ ] Run first in an isolated staging environment with synthetic data. Define rollback and an incident contact before production.
- [ ] Pin container images by digest, dependencies by lockfile, and model files by immutable revision plus SHA-256.
- [ ] Do not mark any gate green because a script or CI job merely exists; retain command output, timestamps, host identity (redacted), and reviewer sign-off.

## 1. WireGuard and host network

### Required design inputs

- [ ] Assign non-overlapping private tunnel addresses and a documented peer inventory.
- [ ] Define the minimum allowed routes per peer; do not advertise broad LAN routes by default.
- [ ] Identify the UDP listen port, approved endpoint addresses, DNS policy, and an out-of-band recovery path.
- [ ] Use a unique private/public key pair per host. Private keys must be generated and stored on the target host, never in this repository or CI logs.
- [ ] Apply host firewall rules that allow only the WireGuard UDP endpoint and explicitly required application traffic; deny unsolicited inbound traffic by default.
- [ ] Record IPv4 and IPv6 policy separately; avoid an accidental IPv6 bypass.

### Staging acceptance tests

- [ ] The WireGuard status command reports only expected peers and a recent handshake for each expected online peer.
- [ ] An approved peer can reach only its explicitly allowed destinations and ports.
- [ ] A peer with an unknown public key cannot establish a tunnel.
- [ ] A revoked peer no longer has an active configuration and cannot reach protected services after the documented revocation propagation interval.
- [ ] Direct access to protected application ports from outside the tunnel is blocked.
- [ ] Reboot and service restart preserve the intended policy.
- [ ] Packet captures/logs confirm no unintended plaintext application traffic crosses the untrusted network.
- [ ] Rollback has been rehearsed without locking out the operator.

Do not apply generic firewall commands blindly to a remote host: rules are OS- and provider-specific and can sever management access. Stage and review the exact rules for each target before applying them.

## 2. mTLS certificate lifecycle

### Issuance and trust

- [ ] Select an approved internal CA/PKI and define trust roots, identity naming, validity periods, key algorithm, and rotation overlap.
- [ ] Issue a distinct certificate per service/client with a narrowly scoped identity (URI SAN or equivalent); do not rely on Common Name alone.
- [ ] Store private keys with restrictive filesystem permissions or a supported secret/key store.
- [ ] Configure the server to require and validate client certificates, chain, validity, identity allowlist, and intended key usage.
- [ ] Define certificate renewal before expiry and alert on upcoming expiration.
- [ ] Define revocation behavior supported by the chosen PKI (CRL/OCSP or short-lived certificates plus denylist); prove that revocation reaches every verifier.

### Negative tests (must fail closed)

- [ ] No client certificate.
- [ ] Certificate signed by an untrusted CA.
- [ ] Expired certificate.
- [ ] Not-yet-valid certificate (where the test environment can safely simulate it).
- [ ] Wrong identity/SAN.
- [ ] Revoked certificate.
- [ ] Certificate/key mismatch.
- [ ] Valid certificate presented to an endpoint outside its authorization scope.
- [ ] Expired or unavailable revocation metadata follows a documented fail-closed policy for protected endpoints.

Save only redacted test summaries; never publish private keys, bearer tokens, or complete sensitive handshake logs. A successful TLS handshake alone does not prove application authorization.

## 3. Encrypted data migration and restore

### Before migration

- [ ] Identify the exact source store, version, record count, schema, attachments, indexes, and data owner approval.
- [ ] Classify personal/sensitive fields; document retention, deletion, and legal basis before copying any real data.
- [ ] Create an encrypted, access-controlled backup in a separate failure domain; test that the backup can be read by the designated recovery identity.
- [ ] Generate a manifest with file/record counts, sizes, schema version, and SHA-256 hashes where applicable. Do not put sensitive record content in the manifest.
- [ ] Run the migration on a representative synthetic or approved staging copy first.
- [ ] Establish a write freeze or a documented dual-write/cutover strategy to avoid lost concurrent updates.

### Migration and acceptance

- [ ] Use the existing migration utility only after confirming its source/target backend and encryption settings match this deployment.
- [ ] Keep the original store unchanged until acceptance and the retention period has elapsed.
- [ ] Verify record counts, schema, required fields, attachments, indexes, access controls, and encryption at rest/in transit.
- [ ] Compare deterministic hashes for immutable payloads; for transformed data, use a documented field-level reconciliation rather than expecting identical hashes.
- [ ] Test representative application queries and authorization boundaries against the target store.
- [ ] Restore the encrypted backup into a clean isolated environment and repeat the integrity checks.
- [ ] Measure and record restore time and recovery point; compare them with the agreed RTO/RPO.
- [ ] Perform cutover only after data owner and technical reviewer sign off; define an explicit rollback trigger and procedure.
- [ ] Securely dispose of temporary exports according to retention policy, with evidence, only after the new store and backup are accepted.

Never run a production migration from a GitHub Actions runner or commit an export to the repository.

## 4. Local MKAOS model: provenance, training, and release

### Model/data approval gate

- [ ] Choose the base model by exact repository/revision and verify its license permits the intended use.
- [ ] Record model architecture, tokenizer, quantization, runtime compatibility, hardware requirements, and upstream provenance.
- [ ] Approve each dataset for rights, privacy, consent/retention, language coverage, data quality, and contamination risk.
- [ ] Remove secrets and personal data that are not authorized for training. Keep an auditable dataset manifest and content hashes, not raw private samples.
- [ ] Split train/validation/test data by source or document family to reduce leakage; keep the final test set sealed from training and tuning.
- [ ] Start with a reproducible baseline and parameter-efficient fine-tuning only if evaluation shows a justified need. Retrieval/orchestration is not model training.
- [ ] Pin random seeds, code/dependency revisions, training configuration, base model revision, and dataset manifest hashes.

### Checkpoint and inference acceptance

- [ ] Save a checkpoint plus tokenizer/configuration and a complete SHA-256 manifest.
- [ ] Verify the manifest from a clean directory and load the checkpoint using the intended local inference runtime.
- [ ] Run a CPU-first smoke test, then benchmark target hardware for latency, memory/VRAM, throughput, and cold start.
- [ ] Demonstrate offline inference with network egress blocked after artifacts are provisioned.
- [ ] Confirm prompt/data logs do not leak sensitive content and model outputs cannot invoke privileged tools without policy checks.
- [ ] Preserve a known-good prior model and prove rollback.

### Independent Turkish quality evaluation

- [ ] Use a frozen Turkish evaluation set that was not used for training or prompt tuning.
- [ ] Cover Turkish grammar/fluency, factuality, instruction following, reasoning, safety, refusal quality, retrieval-grounded answers, and robustness to prompt injection.
- [ ] Compare against a documented baseline with identical prompts and decoding settings.
- [ ] Use a rubric, blinded human review by at least two evaluators for a representative sample, disagreement resolution, and confidence intervals where sample size supports them.
- [ ] Report category-level scores, failure examples with sensitive data removed, latency and hardware, model/data revisions, and known limitations.
- [ ] Define minimum acceptance thresholds before scoring; do not select thresholds after seeing the results.
- [ ] Publish the model card and evaluation report before calling a checkpoint production-approved.

No weights, dataset, target hardware, or human evaluation can be conjured by repository changes alone. Until these gates are met, describe the model as experimental/local-runtime groundwork rather than a production-trained Turkish model.

## 5. Operations and additional features recommended before general availability

Priority order:

1. **Observability and audit:** structured redacted logs, metrics, trace/correlation IDs, health/readiness endpoints, and tamper-evident security event retention.
2. **Incident response:** documented key-compromise response, peer/certificate revocation drill, restore drill, escalation contacts, and post-incident review.
3. **Secrets and supply chain:** secret scanning, dependency/container scanning, SBOM, signed release artifacts, provenance attestations, and pinned action versions.
4. **Identity and authorization:** least privilege, service-to-service scopes, admin MFA, session revocation, and auditable privileged actions.
5. **Abuse protection:** rate limits, quotas, request size/time limits, input validation, prompt-injection defenses, and egress allowlists for agent tools.
6. **Reliability:** health checks, bounded retries, timeouts, circuit breakers, idempotent jobs, queue back-pressure, and graceful degradation.
7. **Privacy controls:** retention/deletion workflows, data export controls, per-tenant isolation, and redaction of prompts/results from telemetry.
8. **Model governance:** model/data cards, evaluation regression suite, rollbackable model registry, versioned prompts, and release approval.
9. **Disaster recovery:** separate encrypted backups, scheduled restore exercises, documented RTO/RPO, and recovery evidence.
10. **Accessibility and Turkish UX:** clear local/offline status, source/provenance disclosure, understandable error states, and accessible keyboard/screen-reader support.

## 6. Release evidence record

For each gate, attach a reviewed record containing:

- Gate ID and result (PASS, FAIL, BLOCKED, or NOT RUN)
- UTC timestamp and environment identifier (redacted as necessary)
- Exact tool/script version and command
- Exit status and artifact/log reference
- Test case, expected result, actual result
- Reviewer and follow-up issue for any failure

A blocked or unrun test is not a pass. Do not publish a “production ready” claim until all mandatory gates pass in the actual target environment.
