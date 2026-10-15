# Offline smoke test for the local SBOM generator.
import json
import tempfile
import unittest
from pathlib import Path
from tools.generate_mkaos_sbom import generate

class SbomGeneratorTests(unittest.TestCase):
    def test_cyclonedx_report_is_marked_for_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            req = root / 'requirements.txt'
            req.write_text('fastapi>=0.1\n', encoding='utf-8')
            out = root / 'sbom.json'
            report = generate(out, req)
            bom = json.loads(out.read_text(encoding='utf-8'))
        self.assertEqual(bom['bomFormat'], 'CycloneDX')
        self.assertEqual(bom['specVersion'], '1.5')
        self.assertGreater(report['components'], 0)
        self.assertEqual(report['status'], 'INCOMPLETE_REQUIRES_HUMAN_REVIEW')
        self.assertEqual(bom['metadata']['properties'][0]['value'], 'INCOMPLETE_REQUIRES_HUMAN_REVIEW')

if __name__ == '__main__':
    unittest.main()
