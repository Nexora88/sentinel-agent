import os
import unittest
from unittest.mock import patch

from core.post_quantum import post_quantum_status


class PostQuantumStatusTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            status = post_quantum_status()
        self.assertFalse(status.enabled)
        self.assertFalse(status.provider_available)
        self.assertFalse(status.production_ready)

    def test_experimental_profile_fails_closed_without_provider(self):
        with patch.dict(os.environ, {"MKAOS_PQ_PROFILE": "experimental"}):
            try:
                import oqs  # noqa: F401
            except ImportError:
                with self.assertRaisesRegex(RuntimeError, "no classical fallback"):
                    post_quantum_status()
            else:
                self.skipTest("liboqs-python installed; provider-specific integration test required")


if __name__ == "__main__":
    unittest.main()
