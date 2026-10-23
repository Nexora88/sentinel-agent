"""Mutual-TLS context builders for an explicitly configured private agent mesh.

These functions configure TLS policy; they do not create a listener, issue certificates,
enroll peers, or prove network deployment security. After a successful TLS handshake,
call verify_peer_certificate() and enforce its allowlist/revocation result before
accepting any task envelope.
"""
from __future__ import annotations

import ssl
from pathlib import Path
from typing import Iterable

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtensionOID

_SAN_PREFIX = "spiffe://mkaos/agent/"


def _require_file(path: str, label: str) -> str:
    candidate = Path(path)
    if not candidate.is_file():
        raise FileNotFoundError(f"{label} file not found: {candidate}")
    return str(candidate)


def create_client_context(*, ca_file: str, cert_file: str, key_file: str) -> ssl.SSLContext:
    """Verify server chain/hostname, require TLS 1.3+, and present a client certificate."""
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=_require_file(ca_file, "CA"))
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(
        _require_file(cert_file, "Client certificate"),
        _require_file(key_file, "Client private key"),
    )
    return context


def create_server_context(*, ca_file: str, cert_file: str, key_file: str) -> ssl.SSLContext:
    """Require client certificates from the configured CA, using TLS 1.3 or newer."""
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.load_cert_chain(
        _require_file(cert_file, "Server certificate"),
        _require_file(key_file, "Server private key"),
    )
    context.load_verify_locations(cafile=_require_file(ca_file, "CA"))
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def verify_peer_certificate(
    certificate_der: bytes,
    *,
    allowed_agent_ids: Iterable[str],
    revoked_sha256_fingerprints: Iterable[str] = (),
) -> str:
    """Return an allowlisted agent ID from a URI SAN or fail closed.

    Call this after TLS handshake using SSLSocket.getpeercert(binary_form=True).
    Revocation fingerprints are SHA-256 hex strings; colons are optional.
    """
    if not isinstance(certificate_der, bytes) or not certificate_der:
        raise ValueError("Peer certificate is required.")
    certificate = x509.load_der_x509_certificate(certificate_der)
    fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
    revoked = {item.replace(":", "").strip().lower() for item in revoked_sha256_fingerprints}
    if fingerprint in revoked:
        raise ValueError("Peer certificate has been revoked.")
    try:
        san = certificate.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        ).value
        identities = [
            name[len(_SAN_PREFIX):]
            for name in san.get_values_for_type(x509.UniformResourceIdentifier)
            if name.startswith(_SAN_PREFIX)
        ]
    except x509.ExtensionNotFound as exc:
        raise ValueError("Peer certificate is missing its URI identity SAN.") from exc
    allowed = set(allowed_agent_ids)
    if len(identities) != 1 or not identities[0] or identities[0] not in allowed:
        raise ValueError("Peer certificate identity is missing, ambiguous, or not allowlisted.")
    return identities[0]
