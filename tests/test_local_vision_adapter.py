import unittest
from core.media.generation_bridge import LocalVisionAdapter

class LocalVisionCapabilityTests(unittest.TestCase):
    def test_disabled_without_explicit_model(self):
        adapter = LocalVisionAdapter(base_url="http://127.0.0.1:11434", model="")
        self.assertFalse(adapter.capabilities()["enabled"])
        self.assertEqual(adapter.capabilities()["operations"], [])

    def test_public_endpoint_is_rejected(self):
        adapter = LocalVisionAdapter(base_url="https://example.com", model="llava")
        self.assertFalse(adapter.capabilities()["enabled"])

    def test_loopback_and_named_model_enable_only_image_understanding(self):
        adapter = LocalVisionAdapter(base_url="http://127.0.0.1:11434", model="llava")
        caps = adapter.capabilities()
        self.assertTrue(caps["enabled"])
        self.assertEqual(caps["operations"], ["understand_image"])
        self.assertIn("no model download", caps["policy"])

if __name__ == "__main__":
    unittest.main()
