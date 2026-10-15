import unittest
from core.hardware_backends import backend_registry, probe_backend


class HardwareBackendTests(unittest.TestCase):
    def test_all_accelerators_are_unverified_by_default(self):
        items = {item["name"]: item for item in backend_registry()}
        self.assertTrue(items["cpu"]["inference_supported"])
        for name in ("nvidia_cuda", "amd_rocm", "apple_metal", "intel_gaudi", "npu_tpu"):
            self.assertEqual(items[name]["status"], "not_probed")
            self.assertFalse(items[name]["inference_supported"])

    def test_probe_pass_is_not_equivalent_to_production_support(self):
        result = probe_backend("amd_rocm", lambda: (True, "simulated test"))
        self.assertEqual(result["status"], "probe_passed_not_benchmarked")
        self.assertFalse(result["inference_supported"])

    def test_unknown_backend_is_rejected(self):
        with self.assertRaises(ValueError):
            probe_backend("imaginary_accelerator", lambda: (True, "x"))


if __name__ == "__main__":
    unittest.main()
