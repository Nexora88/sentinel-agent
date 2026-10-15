"""Mutual-TLS context builders for an explicitly configured private agent mesh.

These functions configure TLS policy; they do not create a listener, issue certificates,
enroll peers, rotate/revoke PKI certificates, or prove network deployment security.
"""
from __future__ import annotations
import ssl
from pathlib import Path

def _require_file(path: str, label: str) -> str:
    candidate = Path(path)
    if not candidate.is_file():
        raise FileNotFoundError(f"{label} file not found: {candidate}")
    return str(candidate)

def create_client_context(*, ca_file: str, cert_file: str, key_file: str) -> ssl.SSLContext:
    """Verify server certificate chain and hostname, and present a client certificate."""
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=_require_file(ca_file, "CA"))
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(_require_file(cert_file, "Client certificate"),
                            _require_file(key_file, "Client private key"))
    return context

def create_server_context(*, ca_file: str, cert_file: str, key_file: str) -> ssl.SSLContext:
    """Require client certificates signed by the configured CA."""
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(_require_file(cert_file, "Server certificate"),
                            _require_file(key_file, "Server private key"))
    context.load_verify_locations(cafile=_require_file(ca_file, "CA"))
    context.verify_mode = ssl.CERT_REQUIRED
    return context
