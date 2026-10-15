import tempfile, unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core.agent_mesh import MeshMessageError, sign_task
from core.mesh_replay import DurableMeshVerifier
class DurableMeshTests(unittest.TestCase):
 def test_duplicate_after_restart(self):
  with tempfile.TemporaryDirectory() as d:
   path=str(Path(d)/'replay.sqlite3'); key=Ed25519PrivateKey.generate()
   env=sign_task(sender_id='ankara',recipient_id='istanbul',task_id='stable',task_type='plan',payload={'goal':'test'},private_key=key,now=1000)
   DurableMeshVerifier(local_agent_id='istanbul',trusted_peers={'ankara':key.public_key()},database_path=path).verify(env,now=1001)
   verifier=DurableMeshVerifier(local_agent_id='istanbul',trusted_peers={'ankara':key.public_key()},database_path=path)
   with self.assertRaisesRegex(MeshMessageError,'Duplicate'): verifier.verify(env,now=1002)
if __name__=='__main__': unittest.main()
