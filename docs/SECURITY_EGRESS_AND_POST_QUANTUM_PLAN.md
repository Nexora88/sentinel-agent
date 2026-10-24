# MKAOS Cryptographic Agility and Post-Quantum Migration Plan

Status: inventory and migration plan only. This document does **not** claim that MKAOS is post-quantum secure.

## Goals

- Keep network access deny-by-default inside the Python web process.
- Identify cryptographic dependencies and protocol boundaries before changing algorithms.
- Prefer standardized, reviewed implementations over home-grown cryptography.
- Preserve a migration path for hybrid classical + post-quantum key establishment where supported.
- Avoid paid infrastructure and avoid introducing heavyweight cryptographic dependencies until an actual use case requires them.

## Initial inventory checklist

For every cryptographic use, record the file, purpose, algorithm, key size, implementation/library, data lifetime, protocol peers, and migration risk.

- [ ] Authentication/session signing and password hashing
- [ ] WebAuthn/passkey authentication and relying-party configuration
- [ ] Signed approval protocol and trust roots
- [ ] Checkpoint SHA-256 integrity checks (integrity hash, not a signature)
- [ ] TLS termination and outbound HTTPS dependencies
- [ ] Artifact provenance, release signing, and update verification
- [ ] Any future model/API identity, encrypted storage, or key exchange

## Migration stages

1. **Inventory (now, no extra runtime dependencies):** map each use to its code path and distinguish hashes, signatures, key exchange, and password hashing. Do not label SHA-256 integrity checks as authentication.
2. **Threat model:** identify attackers, stored-data lifetime, trust boundaries, and whether harvest-now/decrypt-later is relevant to each channel.
3. **Standards check:** evaluate NIST-standardized ML-KEM for key establishment and ML-DSA / SLH-DSA for signatures only where the protocol needs those capabilities. Use maintained libraries and verify platform support; do not implement primitives directly.
4. **Hybrid rollout:** where a supported protocol/library permits it, pilot hybrid classical + post-quantum key establishment, record downgrade behavior, and test interoperability.
5. **Operational proof:** pin dependency versions, publish an algorithm inventory, test key rotation and recovery, and report unsupported paths as gaps.
6. **Release gate:** no "post-quantum secure" claim until a documented threat model, implementation review, interoperability tests, and deployment configuration evidence exist.

## Egress enforcement boundary

`core/safety/egress_policy.py` blocks Python TCP `connect` and `connect_ex` calls unless the destination is loopback or resolves to a public IP covered by `MKAOS_EGRESS_ALLOWLIST` (`host:port`, comma-separated). The default allowlist is empty. Private, link-local, multicast, and other non-global destinations are denied.

This guard is defense in depth, not a host firewall: native extensions, child processes, UDP/DNS, other runtimes, and kernel-level paths may bypass it. Production deployments should additionally apply OS/container egress rules, restrict DNS, and test the actual deployment namespace. Do not use an application status flag as proof of air-gapping.

## Cost and quality guardrails

- Unit tests do not make external network calls.
- Training smoke tests use a tiny randomly initialized model and CPU-only dependencies.
- A successful checkpoint/hash/Rust-loader test proves artifact compatibility, **not** useful Turkish language ability.
- No GPU rental, external model API, or paid service is required for this inventory stage.
