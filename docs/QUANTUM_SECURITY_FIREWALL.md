# MKAOS Quantum-Ready Security Boundary

**Status: design and policy gate only — not a deployed quantum-safe firewall.**

MKAOS should prepare for cryptographically relevant quantum computers without claiming that a configuration flag, a local model, or a conventional firewall makes the platform quantum-safe.

## What this layer does now

The module core/safety/crypto_policy.py checks explicit declarations for TLS 1.3, NIST post-quantum algorithm profiles (ML-KEM and ML-DSA), hybrid key establishment, and an external deployment-attestation flag. Missing or unknown values fail closed. A fully declared configuration without external evidence is configured_unverified, never ready.

The module does not create keys, perform encryption, configure TLS, inspect packets, verify a real handshake, or validate who issued an attestation. Treat it as a guardrail/reporting contract until it is wired to a trusted deployment verifier.

## Defense-in-depth architecture

1. **Network boundary:** default-deny outbound connections; explicit destination/port allowlist; DNS and proxy policy; log denied egress. A local process-level check is not a substitute for host/network firewall rules.
2. **Transport:** TLS 1.3 minimum where supported; use a vetted TLS stack and its supported hybrid post-quantum key exchange. Verify the negotiated group from live handshakes. Do not invent custom cryptography.
3. **Post-quantum signatures and identity:** track standardized ML-KEM/ML-DSA support in maintained libraries and protocols. Keep classical interoperability/hybrid mode policy explicit during migration.
4. **Secrets:** least privilege, OS-backed secret storage, rotation, no keys in client bundles or logs, and separate signing/encryption keys.
5. **Supply chain:** pin dependencies/actions, verify release checksums/signatures, generate an SBOM, scan dependencies, and protect CI permissions.
6. **Agent containment:** tool allowlists, read-only defaults, approval for destructive actions, tenant isolation, bounded resource use, and audited policy decisions.
7. **Recovery:** encrypted backups, tested restore, key rotation/revocation runbooks, incident response, and periodic tabletop exercises.

## Threats to design against

- “Harvest now, decrypt later” exposure of long-lived confidential traffic.
- Downgrade or misconfiguration that silently negotiates classical-only cryptography.
- Malicious or compromised tools attempting unauthorized network egress.
- Compromised dependencies, CI credentials, signing keys, or model artifacts.
- False claims of sovereignty/security based only on environment variables or configuration.

## Release gates before claiming quantum readiness

- [ ] Identify data with long confidentiality lifetimes and document retention requirements.
- [ ] Confirm the actual TLS library/proxy supports the selected standardized hybrid key exchange.
- [ ] Capture and verify negotiated algorithms in integration tests against the real endpoint.
- [ ] Verify attestation origin, signature, freshness, and rollback protection; do not trust a boolean from application config.
- [ ] Test downgrade behavior and ensure unsupported algorithms fail closed.
- [ ] Complete dependency/action pinning, SBOM, secret scanning, and egress-denial tests.
- [ ] Have a cryptography/security reviewer assess the deployment and interoperability impact.

## Budget-conscious implementation order

Start with offline unit tests, policy reporting, egress-denial tests, dependency pinning, and a documented threat model. Do not rent GPUs or build custom cryptography for this work. Enable post-quantum algorithms only through maintained, audited TLS/crypto libraries after compatibility and performance tests. Revisit the policy as ecosystem support evolves.

## References

- NIST FIPS 203 — Module-Lattice-Based Key-Encapsulation Mechanism (ML-KEM).
- NIST FIPS 204 — Module-Lattice-Based Digital Signature Standard (ML-DSA).
- NIST Post-Quantum Cryptography project: https://csrc.nist.gov/projects/post-quantum-cryptography

This document is engineering guidance, not a claim of certification or a substitute for an independent security review.
