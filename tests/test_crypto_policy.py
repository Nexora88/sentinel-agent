"""Tests for the conservative MKAOS cryptographic posture policy."""
import unittest

from core.safety.crypto_policy import assess_crypto_posture


class CryptoPolicyTests(unittest.TestCase):
    def test_missing_configuration_fails_closed(self):
        result = assess_crypto_posture({})
        self.assertEqual(result["state"], "blocked")
        self.assertFalse(result["ready"])
        self.assertTrue(result["issues"])

    def test_declared_pqc_remains_unverified(self):
        result = assess_crypto_posture({
            "tls_min_version": "1.3",
            "kem": "ML-KEM-768",
            "signature": "ML-DSA-65",
            "hybrid_mode": True,
        })
        self.assertEqual(result["state"], "configured_unverified")
        self.assertFalse(result["ready"])
        self.assertTrue(any("not evidence" in item for item in result["issues"]))

    def test_config_cannot_self_attest_readiness(self):
        config = {
            "tls_min_version": "1.3",
            "kem": "ML-KEM-768",
            "signature": "ML-DSA-65",
            "hybrid_mode": True,
            "deployment_attested": True,
            "attestation_verified": True,
        }
        result = assess_crypto_posture(config)
        self.assertEqual(result["state"], "configured_unverified")
        self.assertFalse(result["ready"])

    def test_legacy_or_unknown_algorithms_are_blocked(self):
        for kem in ("RSA-2048", "unknown", ""):
            with self.subTest(kem=kem):
                result = assess_crypto_posture({
                    "tls_min_version": "1.3",
                    "kem": kem,
                    "signature": "ML-DSA-65",
                    "hybrid_mode": True,
                })
                self.assertEqual(result["state"], "blocked")
                self.assertFalse(result["ready"])

    def test_tls_and_hybrid_requirements_are_enforced(self):
        result = assess_crypto_posture({
            "tls_min_version": "1.2",
            "kem": "ML-KEM-768",
            "signature": "ML-DSA-65",
            "hybrid_mode": False,
        })
        self.assertEqual(result["state"], "blocked")
        self.assertFalse(result["ready"])


if __name__ == "__main__":
    unittest.main()
