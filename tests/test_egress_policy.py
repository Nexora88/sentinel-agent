import unittest

from mkaos_security.egress_policy import EgressPolicy, require_permitted_url


class EgressPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = EgressPolicy(frozenset({"api.example.com", "localhost"}), frozenset({443}))

    def test_allows_exact_https_host(self):
        self.assertTrue(self.policy.permits("https://api.example.com/v1/status"))

    def test_rejects_unlisted_and_suffix_spoof_hosts(self):
        self.assertFalse(self.policy.permits("https://evil.example/"))
        self.assertFalse(self.policy.permits("https://api.example.com.attacker.test/"))

    def test_rejects_http_unless_explicit_loopback_exception(self):
        self.assertFalse(self.policy.permits("http://localhost:443/"))
        self.assertFalse(EgressPolicy(frozenset({"localhost"}), frozenset({80}), True).permits("http://localhost/"))

    def test_rejects_credentials_non_http_and_unapproved_ports(self):
        for url in ("https://user:pass@api.example.com/", "ftp://api.example.com/",
                    "https://api.example.com:8443/", "https:///missing-host"):
            with self.subTest(url=url):
                self.assertFalse(self.policy.permits(url))

    def test_default_port_and_explicit_port_are_equivalent(self):
        self.assertTrue(self.policy.permits("https://api.example.com/"))
        self.assertTrue(self.policy.permits("https://api.example.com:443/"))

    def test_denial_raises_before_request(self):
        with self.assertRaises(PermissionError):
            require_permitted_url("https://untrusted.example/", self.policy)

    def test_exact_allowlist_only_no_wildcard(self):
        with self.assertRaises(ValueError):
            EgressPolicy(frozenset({"*.example.com"}))


if __name__ == "__main__":
    unittest.main()
