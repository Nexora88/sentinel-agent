"""Default-deny outbound destination policy regression tests."""
import unittest
from core.security.egress_policy import EgressDenied, allowed_hosts_from_env, authorize_egress_url


class EgressPolicyTests(unittest.TestCase):
    def setUp(self):
        self.allowed = frozenset({"api.example.com", "updates.example.org"})

    def test_exact_allowlisted_https_host_passes(self):
        url = "https://API.EXAMPLE.COM/v1/status?ok=1"
        self.assertEqual(authorize_egress_url(url, allowed_hosts=self.allowed), url)

    def test_default_policy_denies_every_destination(self):
        with self.assertRaises(EgressDenied):
            authorize_egress_url("https://api.example.com")

    def test_suffix_and_subdomain_spoofing_are_denied(self):
        for host in ("api.example.com.attacker.test", "evil-api.example.com"):
            with self.subTest(host=host), self.assertRaises(EgressDenied):
                authorize_egress_url(f"https://{host}/", allowed_hosts=self.allowed)

    def test_non_https_and_nonstandard_ports_are_denied(self):
        for url in ("http://api.example.com", "https://api.example.com:8443"):
            with self.subTest(url=url), self.assertRaises(EgressDenied):
                authorize_egress_url(url, allowed_hosts=self.allowed)

    def test_local_private_ip_and_credentials_are_denied(self):
        for url in (
            "https://localhost/", "https://service.internal/", "https://127.0.0.1/",
            "https://10.0.0.2/", "https://user:pass@api.example.com/",
        ):
            with self.subTest(url=url), self.assertRaises(EgressDenied):
                authorize_egress_url(url, allowed_hosts=self.allowed)

    def test_malformed_allowlist_entries_fail_closed(self):
        for value in ("*.example.com", "https://example.com", "127.0.0.1", ".example.com"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                allowed_hosts_from_env(value)

    def test_trailing_dot_is_normalized_for_comparison(self):
        self.assertEqual(
            authorize_egress_url("https://api.example.com./", allowed_hosts=self.allowed),
            "https://api.example.com./",
        )


if __name__ == "__main__":
    unittest.main()
