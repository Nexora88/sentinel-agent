"""Conservative cryptographic posture checks for MKAOS.

This module checks declared deployment policy only. It does not implement
cryptography, inspect live TLS handshakes, or attest that a network path is
quantum-resistant. Production enforcement must be provided by the TLS/runtime
stack and verified independently.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_ALLOWED_TLS = {"1.3"}
_ALLOWED_KEMS = {"ML-KEM-768", "ML-KEM-1024"}
_ALLOWED_SIGNATURES = {"ML-DSA-65", "ML-DSA-87"}
_LEGACY_MARKERS = ("RSA", "ECDH", "ECDSA", "DH", "SHA1", "SHA-1")


def assess_crypto_posture(config: Mapping[str, Any]) -> dict[str, Any]:
    """Return a conservative posture report from explicit deployment settings.

    Expected keys: tls_min_version, kem, signature, hybrid_mode,
    deployment_attested.

    Missing, unknown, or legacy settings never count as ready. Even a complete
    declaration remains configured_unverified unless trusted deployment
    evidence is supplied by infrastructure outside this function.
    """
    issues: list[str] = []
    tls = str(config.get("tls_min_version", "")).strip()
    kem = str(config.get("kem", "")).strip().upper()
    signature = str(config.get("signature", "")).strip().upper()
    hybrid_mode = config.get("hybrid_mode") is True
    attested = config.get("deployment_attested") is True

    if tls not in _ALLOWED_TLS:
        issues.append("TLS minimum must be explicitly configured as 1.3.")
    if kem not in _ALLOWED_KEMS:
        issues.append("KEM must explicitly select a supported NIST ML-KEM profile.")
    if signature not in _ALLOWED_SIGNATURES:
        issues.append("Signature must explicitly select a supported NIST ML-DSA profile.")
    if not hybrid_mode:
        issues.append("Hybrid classical + post-quantum key establishment is not enabled.")
    for field, value in (("kem", kem), ("signature", signature)):
        if any(marker in value for marker in _LEGACY_MARKERS):
            issues.append(f"{field} contains a legacy algorithm marker.")

    if issues:
        state = "blocked"
    elif not attested:
        state = "configured_unverified"
        issues.append(
            "Configuration is declarative only; live handshake and deployment are not attested."
        )
    else:
        state = "attested_by_external_evidence"

    return {
        "state": state,
        "ready": state == "attested_by_external_evidence",
        "policy_version": "mkaos-crypto-posture-v1",
        "checks": {
            "tls_min_version": tls or None,
            "kem": kem or None,
            "signature": signature or None,
            "hybrid_mode": hybrid_mode,
            "external_deployment_attestation": attested,
        },
        "issues": issues,
        "limitations": [
            "This is a policy gate, not a firewall or cryptographic implementation.",
            "The caller must validate attestation provenance and live negotiated algorithms.",
            "Post-quantum readiness does not protect against endpoint compromise or bad key management.",
        ],
    }
