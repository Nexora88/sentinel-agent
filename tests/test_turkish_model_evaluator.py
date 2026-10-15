import importlib.util, unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'evaluate_turkish_models.py'
SPEC=importlib.util.spec_from_file_location('evaluate_turkish_models',SCRIPT)
MODULE=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)
class EvaluatorTests(unittest.TestCase):
 def test_remote_endpoint_rejected(self):
  with self.assertRaises(ValueError): MODULE.local_base_url('http://example.com:11434')
 def test_local_endpoint_accepted(self): self.assertEqual(MODULE.local_base_url('http://localhost:11434/'),'http://localhost:11434')
if __name__=='__main__': unittest.main()
