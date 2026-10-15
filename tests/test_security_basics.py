import unittest
from unittest.mock import Mock, patch

from core.permission_manager import Action, PermissionManager
from tools.website_scanner import UnsafeTarget, WebsiteScanner, validate_public_url


class PublicUrlValidationTests(unittest.TestCase):
    def test_blocks_loopback_and_private_addresses(self):
        for url in (
            "http://127.0.0.1",
            "http://10.0.0.2",
            "http://192.168.1.1",
            "http://169.254.169.254/latest/meta-data/",
            "http://[::1]/",
        ):
            with self.subTest(url=url):
                with self.assertRaises(UnsafeTarget):
                    validate_public_url(url)

    def test_rejects_unsupported_scheme_and_embedded_credentials(self):
        for url in ("file:///etc/passwd", "https://user:pass@example.com"):
            with self.subTest(url=url):
                with self.assertRaises(UnsafeTarget):
                    validate_public_url(url)

    def test_accepts_public_literal_ip(self):
        self.assertEqual(validate_public_url("https://8.8.8.8"), "https://8.8.8.8")

    def test_redirect_to_loopback_is_blocked_before_second_request(self):
        scanner = WebsiteScanner()
        first = Mock(status_code=302, headers={"Location": "http://127.0.0.1/admin"})
        scanner.session.get = Mock(return_value=first)
        with patch("tools.website_scanner.socket.getaddrinfo") as resolver:
            resolver.return_value = [(None, None, None, None, ("93.184.216.34", 443))]
            with self.assertRaises(UnsafeTarget):
                scanner._get_public("https://example.com")
        self.assertEqual(scanner.session.get.call_count, 1)


class ApprovalIdentityTests(unittest.TestCase):
    def test_approval_requires_stable_request_id_and_is_one_time(self):
        manager = PermissionManager()
        message = manager.request_approval(Action.PUSH_TO_REMOTE, "push branch", {"branch": "feature"})
        request_id = message.split("Request ID: ", 1)[1].splitlines()[0]
        self.assertTrue(request_id)
        self.assertFalse(manager.approve("0"))
        self.assertTrue(manager.approve(request_id))
        self.assertFalse(manager.approve(request_id))
        self.assertEqual(manager.list_pending(), [])

    def test_rejects_unknown_approval_id(self):
        manager = PermissionManager()
        manager.request_approval(Action.MODIFY_FILES, "edit config")
        self.assertFalse(manager.reject("not-a-real-id"))


if __name__ == "__main__":
    unittest.main()
