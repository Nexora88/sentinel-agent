"""Offline unit tests for application-layer egress policy; no network is used."""
import unittest

from core.safety.egress import EgressPolicy, require_authorized_url


class EgressPolicyTests(unittest.TestCase):
    def test_default_is_deny_all(self):
        self.assertFalse(EgressPolicy().authorize_url("https://example.com").allowed)

    def test_exact_allowlisted_https_host_is_allowed(self):
        policy = EgressPolicy({"api.example.com"})
        self.assertTrue(policy.authorize_url("https://api.example.com/v1").allowed)

    def test_sibling_and_subdomain_are_not_implicitly_allowed(self):
        policy = EgressPolicy({"example.com"})
        self.assertFalse(policy.authorize_url("https://api.example.com").allowed)
        self.assertFalse(policy.authorize_url("https://example.com.attacker.invalid").allowed)

    def test_http_and_nonstandard_ports_are_denied(self):
        policy = EgressPolicy({"api.example.com"})
        self.assertFalse(policy.authorize_url("http://api.example.com").allowed)
        self.assertFalse(policy.authorize_url("https://api.example.com:8443").allowed)

    def test_credentials_and_ip_literal_are_denied_by_default(self):
        policy = EgressPolicy({"api.example.com"})
        self.assertFalse(policy.authorize_url("https://user:pass@api.example.com").allowed)
        self.assertFalse(policy.authorize_url("https://127.0.0.1").allowed)

    def test_malformed_urls_fail_closed(self):
        policy = EgressPolicy({"api.example.com"})
        for url in ("", "https://", "https://api.example.com:bad", "file:///etc/passwd"):
            with self.subTest(url=url):
                self.assertFalse(policy.authorize_url(url).allowed)

    def test_require_authorized_url_raises(self):
        with self.assertRaises(PermissionError):
            require_authorized_url("https://unlisted.example", EgressPolicy({"api.example.com"}))

    def test_allowlist_requires_exact_hostname_format(self):
        for host in ("", ".example.com", "example.com/path", "example.com:443"):
            with self.subTest(host=host):
                with self.assertRaises(ValueError):
                    EgressPolicy({host})


if __name__ == "__main__":
    unittest.main()
