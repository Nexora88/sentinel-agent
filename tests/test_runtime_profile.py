import unittest
from core.runtime_profile import get_runtime_profile


class RuntimeProfileTests(unittest.TestCase):
    def test_low_ram_does_not_promise_large_model(self):
        p = get_runtime_profile(total_ram_mb=2048, system="Linux", machine="aarch64", cpu_count=4)
        self.assertEqual(p["model_guidance"]["tier"], "minimal")
        self.assertIsNone(p["model_guidance"]["suggested_chat_model"])
        self.assertFalse(p["network_requests_made"])

    def test_entry_tier_suggests_small_models(self):
        p = get_runtime_profile(total_ram_mb=8192, system="Windows")
        self.assertEqual(p["model_guidance"]["tier"], "entry")
        self.assertEqual(p["model_guidance"]["suggested_chat_model"], "qwen2.5:1.5b")
        self.assertEqual(p["platform"], "Windows")

    def test_high_tier_does_not_claim_gpu_support(self):
        p = get_runtime_profile(total_ram_mb=32768, machine="x86_64")
        self.assertEqual(p["model_guidance"]["tier"], "high")
        self.assertEqual(p["gpu_backend"], "unknown")
        self.assertTrue(p["limitations_tr"])

    def test_vram_caps_context_without_claiming_gpu_inference_support(self):
        p = get_runtime_profile(total_ram_mb=8192, total_vram_mb=3072)
        self.assertEqual(p["total_vram_mb"], 3072)
        self.assertEqual(p["model_guidance"]["suggested_context_tokens"], 2048)
        self.assertEqual(p["gpu_backend"], "nvidia_detected_unverified")
        self.assertFalse(p["network_requests_made"])

    def test_larger_vram_allows_context_recommendation_to_scale(self):
        p = get_runtime_profile(total_ram_mb=32768, total_vram_mb=12288)
        self.assertEqual(p["model_guidance"]["suggested_context_tokens"], 8192)
        self.assertIn("gerçek model testi gerekir", p["model_guidance"]["reason_tr"])

    def test_zero_ram_uses_minimal_profile(self):
        p = get_runtime_profile(total_ram_mb=0)
        self.assertEqual(p["model_guidance"]["tier"], "minimal")

    def test_cpu_count_is_never_zero(self):
        p = get_runtime_profile(total_ram_mb=4096, cpu_count=0)
        self.assertEqual(p["cpu_count"], 1)


if __name__ == "__main__":
    unittest.main()
