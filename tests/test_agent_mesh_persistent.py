import tempfile, unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core.agent_mesh import MeshMessageError, sign_task
from core.mesh_replay import DurableMeshVerifier

class DurableMeshTests(unittest.TestCase):
    def test_duplicate_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "replay.sqlite3")
            key = Ed25519PrivateKey.generate()
            env = sign_task(sender_id="ankara", recipient_id="istanbul", task_id="stable",
                            task_type="plan", payload={"goal": "test"}, private_key=key, now=1000)
            DurableMeshVerifier(local_agent_id="istanbul", trusted_peers={"ankara": key.public_key()},
                                database_path=path).verify(env, now=1001)
            verifier = DurableMeshVerifier(local_agent_id="istanbul", trusted_peers={"ankara": key.public_key()},
                                            database_path=path)
            with self.assertRaisesRegex(MeshMessageError, "Duplicate"):
                verifier.verify(env, now=1002)

    def test_revoked_peer_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            key = Ed25519PrivateKey.generate()
            verifier = DurableMeshVerifier(local_agent_id="istanbul", trusted_peers={"ankara": key.public_key()},
                                           database_path=str(Path(directory) / "replay.sqlite3"),
                                           revoked_peer_ids={"ankara"})
            env = sign_task(sender_id="ankara", recipient_id="istanbul", task_id="revoked",
                            task_type="plan", payload={}, private_key=key, now=1000)
            with self.assertRaisesRegex(MeshMessageError, "Revoked"):
                verifier.verify(env, now=1001)

    def test_memory_database_rejected(self):
        with self.assertRaisesRegex(ValueError, "file-backed"):
            DurableMeshVerifier(local_agent_id="istanbul", trusted_peers={}, database_path=":memory:")

if __name__ == "__main__":
    unittest.main()
