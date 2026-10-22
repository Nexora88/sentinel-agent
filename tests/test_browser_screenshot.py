import socket
import unittest
from unittest.mock import patch

from scripts.browser_screenshot import _validate_url


def private_dns(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("172.19.0.2", 80))]


def public_dns(*args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))]


class BrowserScreenshotPolicyTests(unittest.TestCase):
    def test_allowlisted_private_fixture_is_accepted(self):
        with patch("scripts.browser_screenshot.socket.getaddrinfo", side_effect=private_dns):
            self.assertEqual(_validate_url("http://browser-fixture:80/", {"browser-fixture"}), "http://browser-fixture:80/")

    def test_public_addresses_and_non_allowlisted_hosts_are_rejected(self):
        with patch("scripts.browser_screenshot.socket.getaddrinfo", side_effect=public_dns):
            with self.assertRaises(ValueError):
                _validate_url("http://browser-fixture/", {"browser-fixture"})
        with patch("scripts.browser_screenshot.socket.getaddrinfo", side_effect=private_dns):
            with self.assertRaises(ValueError):
                _validate_url("http://other-service/", {"browser-fixture"})

    def test_credentials_and_non_http_schemes_are_rejected(self):
        with patch("scripts.browser_screenshot.socket.getaddrinfo", side_effect=private_dns):
            for url in ("http://user:password@browser-fixture/", "file:///etc/passwd", "https://browser-fixture/#secret"):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    _validate_url(url, {"browser-fixture"})


if __name__ == "__main__":
    unittest.main()
