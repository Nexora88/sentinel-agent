# MKAOS Security Roadmap: Post-Quantum Readiness

**Status:** design and implementation roadmap; not a certification or a claim of quantum resistance.

MKAOS should be secure by measurable properties, not by calling a feature a “quantum firewall.” A firewall alone cannot protect a system from compromised dependencies, stolen credentials, malicious model artifacts, unsafe plugins, or a vulnerable endpoint.

## Security goals

1. **Local-first by default.** Network egress is denied unless a feature explicitly requires it. Record the reason, destination, and outcome for allowed egress.
2. **Fail closed.** If a model artifact, signature, digest, permission, policy, or trust decision cannot be validated, do not load or execute it.
3. **Verifiable supply chain.** Pin actions and dependencies where practical; generate an SBOM; scan for secrets; attest release artifacts; verify provenance before accepting updates.
4. **Least privilege.** Keep inference separate from update/install operations. Avoid running model files or extensions as code. Restrict file, process, and network permissions.
5. **Auditable security events.** Record security-relevant decisions without logging passwords, tokens, private prompts, or other sensitive content by default.
6. **Recoverability.** Support signed updates, rollback to a known-good release, and a documented incident-response process.

## Post-quantum cryptography (PQC)

A sufficiently capable fault-tolerant quantum computer could threaten widely used public-key algorithms such as RSA and elliptic-curve cryptography. That does **not** mean current systems can be broken by today's quantum computers, and it does not mean every encryption algorithm is affected equally.

Use a staged migration rather than inventing a proprietary algorithm:

- **Inventory:** list every use of TLS, certificates, SSH, signing, key exchange, encrypted storage, tokens, and third-party cryptographic libraries. Record algorithm, key size, protocol, owner, and data lifetime.
- **Prefer standards:** evaluate NIST-standardized ML-KEM for key establishment and ML-DSA / SLH-DSA for signatures when the ecosystem and threat model support them. Follow current official standards and vendor guidance; do not implement primitives from scratch.
- **Crypto agility:** isolate algorithm selection behind reviewed interfaces so algorithms can be replaced without redesigning the whole application. Version formats and reject unknown or downgraded security settings.
- **Hybrid migration:** where appropriate, use a reviewed hybrid classical + post-quantum protocol supported by maintained libraries, not a home-grown combination. Test interoperability and downgrade resistance.
- **Protect long-lived secrets:** prioritize data that must remain confidential for many years (“harvest now, decrypt later”). Rotation and key-management procedures matter as much as the algorithm.
- **Verify before claiming:** publish the exact library/version, protocol configuration, test evidence, limitations, and supported platforms. Until then, label PQC as “planned” or “not yet enabled.”

## Practical implementation gates

### P0 — baseline (low-cost, CPU-only)
- Keep existing Rust checkpoint SHA-256 verification and fail-closed tests.
- Add malformed/truncated artifact, invalid dimensions, non-finite value, and tokenizer-contract regression tests.
- Keep secrets out of logs and client bundles; run repository secret scanning.
- Generate an SBOM and review dependency/license changes.
- Pin GitHub Actions to immutable commit SHAs before treating CI as a hardened release gate.
- Never publish model weights from experimental CI runs unless redistribution rights are independently confirmed.

### P1 — release integrity
- Sign release manifests and artifacts with a protected release identity; verify signatures before installation.
- Use immutable, versioned release assets rather than moving branch archives. Verify both digest and signature before executing an installer.
- Separate build/test permissions from release permissions; require protected-branch review and environment approval for publishing.
- Test rollback and recovery from a corrupted or interrupted update.

### P2 — PQC migration
- Complete the cryptographic inventory and threat model.
- Select maintained libraries with supported PQC implementations; define platform and compatibility requirements.
- Add interoperability, downgrade, key rotation, and negative tests.
- Roll out behind explicit configuration with a documented fallback policy that does not silently downgrade security.
- Reassess against current NIST and national guidance before each release.

## What this roadmap does not claim

- No “quantum-proof” or “unbreakable” guarantee.
- No custom cryptographic algorithm.
- No PQC protection until an actual implementation is selected, integrated, and tested.
- A successful CI run proves only the checks that ran; skipped jobs are not passes.
- A SHA-256 digest detects byte changes only when the expected digest is trusted. It does not by itself authenticate the publisher.

## Acceptance checklist

- [ ] Threat model and data-classification inventory reviewed.
- [ ] Egress policy tested with network disabled and with denied destinations.
- [ ] Artifact integrity failures stop loading.
- [ ] Release signature and publisher identity are verified before installation.
- [ ] SBOM and dependency review are attached to each release.
- [ ] PQC algorithm/library/configuration and test evidence documented before any PQC claim.
