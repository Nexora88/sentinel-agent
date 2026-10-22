"""Experimental real ML-KEM / ML-DSA operations via a reviewed liboqs-python provider.

This is a crypto primitive adapter, not a production protocol. It does not persist keys,
negotiate versions, encrypt application memory, or claim FIPS validation. Keep disabled
until key lifecycle, interoperability and threat-model reviews are complete.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


class PostQuantumUnavailable(RuntimeError):
    pass


def _provider():
    if os.getenv("MKAOS_PQ_PROFILE", "disabled").strip().lower() != "experimental":
        raise PostQuantumUnavailable("Post-quantum operations require MKAOS_PQ_PROFILE=experimental.")
    try:
        import oqs  # type: ignore[import-not-found]
    except ImportError as exc:
        raise PostQuantumUnavailable("liboqs-python provider is not installed; no fallback is permitted.") from exc
    kem = set(oqs.get_enabled_kem_mechanisms())
    signatures = set(oqs.get_enabled_sig_mechanisms())
    if "ML-KEM-768" not in kem or "ML-DSA-65" not in signatures:
        raise PostQuantumUnavailable("Provider must expose ML-KEM-768 and ML-DSA-65.")
    return oqs


@dataclass(frozen=True)
class KemKeyPair:
    public_key: bytes
    secret_key: bytes


@dataclass(frozen=True)
class SignatureKeyPair:
    public_key: bytes
    secret_key: bytes


def generate_kem_keypair() -> KemKeyPair:
    """Generate an ephemeral ML-KEM-768 keypair. Caller must protect the secret key."""
    oqs = _provider()
    with oqs.KeyEncapsulation("ML-KEM-768") as kem:
        public = kem.generate_keypair()
        secret = kem.export_secret_key()
    if not public or not secret:
        raise PostQuantumUnavailable("Provider returned an empty ML-KEM key.")
    return KemKeyPair(bytes(public), bytes(secret))


def encapsulate(public_key: bytes) -> tuple[bytes, bytes]:
    """Return (ciphertext, shared_secret) for ML-KEM-768."""
    if not isinstance(public_key, bytes) or not public_key:
        raise ValueError("public_key must be non-empty bytes")
    oqs = _provider()
    with oqs.KeyEncapsulation("ML-KEM-768") as kem:
        ciphertext, shared_secret = kem.encap_secret(public_key)
    if not ciphertext or not shared_secret:
        raise PostQuantumUnavailable("Provider returned empty encapsulation output.")
    return bytes(ciphertext), bytes(shared_secret)


def decapsulate(ciphertext: bytes, secret_key: bytes) -> bytes:
    """Recover the ML-KEM shared secret. Secret-key storage is the caller's responsibility."""
    if not isinstance(ciphertext, bytes) or not ciphertext or not isinstance(secret_key, bytes) or not secret_key:
        raise ValueError("ciphertext and secret_key must be non-empty bytes")
    oqs = _provider()
    with oqs.KeyEncapsulation("ML-KEM-768", secret_key=secret_key) as kem:
        secret = kem.decap_secret(ciphertext)
    if not secret:
        raise PostQuantumUnavailable("Provider returned an empty shared secret.")
    return bytes(secret)


def generate_signature_keypair() -> SignatureKeyPair:
    """Generate an ML-DSA-65 keypair for message signing."""
    oqs = _provider()
    with oqs.Signature("ML-DSA-65") as signature:
        public = signature.generate_keypair()
        secret = signature.export_secret_key()
    if not public or not secret:
        raise PostQuantumUnavailable("Provider returned an empty ML-DSA key.")
    return SignatureKeyPair(bytes(public), bytes(secret))


def sign(message: bytes, secret_key: bytes) -> bytes:
    """Sign bytes using ML-DSA-65; callers must protect and rotate secret keys."""
    if not isinstance(message, bytes) or not isinstance(secret_key, bytes) or not secret_key:
        raise ValueError("message and non-empty secret_key must be bytes")
    oqs = _provider()
    with oqs.Signature("ML-DSA-65", secret_key=secret_key) as signature:
        result = signature.sign(message)
    if not result:
        raise PostQuantumUnavailable("Provider returned an empty signature.")
    return bytes(result)


def verify(message: bytes, signature_bytes: bytes, public_key: bytes) -> bool:
    """Verify an ML-DSA-65 signature; malformed inputs return False."""
    if not all(isinstance(item, bytes) and item for item in (signature_bytes, public_key)):
        return False
    if not isinstance(message, bytes):
        return False
    oqs = _provider()
    with oqs.Signature("ML-DSA-65") as signature:
        try:
            return bool(signature.verify(message, signature_bytes, public_key))
        except (ValueError, TypeError):
            return False
