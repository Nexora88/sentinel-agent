import unittest
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from core.mesh_tls import verify_peer_certificate


def make_certificate():
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "MKAOS test CA")])
    now = datetime.now(timezone.utc)
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    peer_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    peer = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "agent-a")]))
        .issuer_name(ca.subject)
        .public_key(peer_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([x509.UniformResourceIdentifier("spiffe://mkaos/agent/agent-a")]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return peer.public_bytes(serialization.Encoding.DER)


class MeshTLSIdentityTests(unittest.TestCase):
    def test_allowlisted_identity_is_extracted(self):
        cert = make_certificate()
        self.assertEqual(verify_peer_certificate(cert, allowed_agent_ids={"agent-a"}), "agent-a")

    def test_unknown_peer_and_revoked_certificate_are_rejected(self):
        cert_der = make_certificate()
        cert = x509.load_der_x509_certificate(cert_der)
        fingerprint = cert.fingerprint(hashes.SHA256()).hex()
        with self.assertRaises(ValueError):
            verify_peer_certificate(cert_der, allowed_agent_ids={"agent-b"})
        with self.assertRaises(ValueError):
            verify_peer_certificate(cert_der, allowed_agent_ids={"agent-a"}, revoked_sha256_fingerprints={fingerprint})


if __name__ == "__main__":
    unittest.main()
