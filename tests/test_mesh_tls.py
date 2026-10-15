import unittest
from core.mesh_tls import create_client_context
class MeshTlsTests(unittest.TestCase):
 def test_missing_ca(self):
  with self.assertRaises(FileNotFoundError): create_client_context(ca_file='missing-ca.pem',cert_file='missing-cert.pem',key_file='missing-key.pem')
if __name__ == '__main__': unittest.main()
