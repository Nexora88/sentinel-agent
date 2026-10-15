import os
import unittest
from unittest.mock import patch
from core.integrations.catalog import authorize_integration_action, integration_status

class IntegrationCatalogTests(unittest.TestCase):
    def test_status_never_returns_secret_values(self):
        secret = "do-not-return-this-secret"
        with patch.dict(os.environ, {"GITHUB_TOKEN": secret, "MKAOS_NETWORK_MODE": "online"}, clear=True):
            status = integration_status()
        self.assertEqual(status["github"]["state"], "configured_unverified")
        self.assertNotIn(secret, repr(status))

    def test_network_integrations_blocked_offline(self):
        with patch.dict(os.environ, {"MKAOS_NETWORK_MODE": "offline"}, clear=True):
            self.assertEqual(integration_status()["github"]["state"], "blocked_offline")
            with self.assertRaisesRegex(PermissionError, "Çevrimdışı"):
                authorize_integration_action("github", "read:repos")

    def test_write_requires_explicit_approval(self):
        with patch.dict(os.environ, {"MKAOS_NETWORK_MODE": "online", "GITHUB_TOKEN": "dummy"}, clear=True):
            with self.assertRaisesRegex(PermissionError, "açık kullanıcı onayı"):
                authorize_integration_action("github", "create_issue")
            result = authorize_integration_action("github", "create_issue", approved=True)
        self.assertEqual(result["authorization"], "approved_write")

    def test_unknown_action_fails_closed(self):
        with self.assertRaises(PermissionError):
            authorize_integration_action("github", "delete_everything", approved=True, network_allowed=True)

    def test_unknown_integration_fails_closed(self):
        with self.assertRaises(ValueError):
            authorize_integration_action("imaginary", "read:data")

    def test_local_media_does_not_require_network(self):
        with patch.dict(os.environ, {"MKAOS_NETWORK_MODE": "offline"}, clear=True):
            self.assertEqual(integration_status()["local_audio"]["state"], "local_dependency_check_required")
            self.assertEqual(authorize_integration_action("local_audio", "read:transcribe")["authorization"], "read_allowed")

if __name__ == "__main__":
    unittest.main()
