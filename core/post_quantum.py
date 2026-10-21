"""Experimental post-quantum cryptography capability gate.

This module deliberately does not replace Ed25519 or encrypt memory files yet.
It exposes an opt-in, fail-closed capability check for a separately installed
liboqs-python binding. Production integration requires interoperability,
persistence, rotation, and migration tests before use.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PostQuantumStatus:
    enabled: bool
    provider_available: bool
    kem_algorithm: str
    signature_algorithm: str
    production_ready: bool = False


def post_quantum_status() -> PostQuantumStatus:
    """Report experimental provider availability without silently falling back."""
    enabled = os.getenv("MKAOS_PQ_PROFILE", "disabled").strip().lower() == "experimental"
    if not enabled:
        return PostQuantumStatus(False, False, "ML-KEM-768", "ML-DSA-65")
    try:
        import oqs  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "Experimental post-quantum profile requested, but liboqs-python is unavailable. "
            "Install and pin a reviewed provider build; no classical fallback is performed."
        ) from exc

    kem = set(oqs.get_enabled_kem_mechanisms())
    sig = set(oqs.get_enabled_sig_mechanisms())
    available = "ML-KEM-768" in kem and "ML-DSA-65" in sig
    if not available:
        raise RuntimeError(
            "Configured provider does not expose both ML-KEM-768 and ML-DSA-65; "
            "experimental profile remains unavailable."
        )
    return PostQuantumStatus(True, True, "ML-KEM-768", "ML-DSA-65")
