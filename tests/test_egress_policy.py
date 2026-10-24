"""Unit tests for MKAOS fail-closed outbound TCP policy; no network probes."""
import os
import unittest
from unittest.mock import patch

from core.safety.egress_policy import EgressDenied, check_destination, _allowlist


class EgressPolicyTests(unittest.TestCase):
    def test_public_destination_denied_when_allowlist_empty(self):
        with patch.dict(os.environ, {"MKAOS_EGRESS_ALLOWLIST": ""}):
            with self.assertRaises(EgressDenied):
                check_destination(("1.1.1.1", 443))

    def test_loopback_is_available_for_local_model_services(self):
        check_destination(("127.0.0.1", 11434))
        check_destination(("::1", 8080, 0, 0))

    def test_private_lan_destination_is_denied(self):
        with self.assertRaises(EgressDenied):
            check_destination(("192.168.1.10", 443))

    def test_parser_accepts_host_port(self):
        with patch.dict(os.environ, {"MKAOS_EGRESS_ALLOWLIST": "api.example.org:443"}):
            self.assertEqual(_allowlist(), {("api.example.org", 443)})

    def test_parser_rejects_invalid_port(self):
        with patch.dict(os.environ, {"MKAOS_EGRESS_ALLOWLIST": "api.example.org:99999"}):
            with self.assertRaises(ValueError):
                _allowlist()


if __name__ == "__main__":
    unittest.main()
