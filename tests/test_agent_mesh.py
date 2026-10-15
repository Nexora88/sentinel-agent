import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core.agent_mesh import MeshMessageError, MeshVerifier, sign_task


class AgentMeshTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.verifier = MeshVerifier(local_agent_id="istanbul-1",
                                     trusted_peers={"ankara-1": self.private.public_key()})

    def envelope(self, **kwargs):
        base = dict(sender_id="ankara-1", recipient_id="istanbul-1", task_id="task-1",
                    task_type="plan", payload={"goal": "summarize test report"},
                    private_key=self.private, now=1000, ttl_seconds=60)
        base.update(kwargs)
        return sign_task(**base)

    def test_valid_message_verifies_once(self):
        envelope = self.envelope()
        task = self.verifier.verify(envelope, now=1010)
        self.assertEqual(task.sender_id, "ankara-1")
        with self.assertRaisesRegex(MeshMessageError, "Duplicate"):
            self.verifier.verify(envelope, now=1011)

    def test_tampered_payload_rejected(self):
        envelope = self.envelope()
        envelope["payload"]["goal"] = "tampered"
        with self.assertRaisesRegex(MeshMessageError, "Signature"):
            self.verifier.verify(envelope, now=1010)

    def test_expired_message_rejected(self):
        with self.assertRaisesRegex(MeshMessageError, "expired"):
            self.verifier.verify(self.envelope(), now=1100)

    def test_unauthorized_task_type_rejected(self):
        with self.assertRaisesRegex(MeshMessageError, "allowlist"):
            self.envelope(task_type="shell")

    def test_executable_payload_rejected(self):
        with self.assertRaisesRegex(MeshMessageError, "Executable"):
            self.envelope(payload={"command": "whoami"})

    def test_nested_executable_payload_rejected(self):
        with self.assertRaisesRegex(MeshMessageError, "Executable"):
            self.envelope(payload={"metadata": {"script": "unsafe"}})

    def test_wrong_recipient_rejected(self):
        envelope = self.envelope(recipient_id="another-agent")
        with self.assertRaisesRegex(MeshMessageError, "recipient"):
            self.verifier.verify(envelope, now=1010)


if __name__ == "__main__":
    unittest.main()
