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


    def test_torch_probe_reports_cpu_without_claiming_inference_support(self):
        class FakeCuda:
            @staticmethod
            def is_available():
                return False
        class FakeTorch:
            cuda = FakeCuda()
        result = __import__("core.hardware_backends", fromlist=["probe_training_runtime"]).probe_training_runtime(FakeTorch())
        self.assertEqual(result["training_runtime"], "cpu")
        self.assertTrue(result["pytorch_available"])
        self.assertFalse(result["inference_supported"])

    def test_torch_probe_distinguishes_rocm_from_cuda(self):
        class FakeProperties:
            total_memory = 8 * 1024**3
        class FakeCuda:
            @staticmethod
            def is_available():
                return True
            @staticmethod
            def get_device_name(_index):
                return "Mock GPU"
            @staticmethod
            def device_count():
                return 1
            @staticmethod
            def get_device_properties(_index):
                return FakeProperties()
            @staticmethod
            def is_bf16_supported():
                return True
        class FakeVersion:
            hip = "6.2"
        class FakeTorch:
            cuda = FakeCuda()
            version = FakeVersion()
        from core.hardware_backends import probe_training_runtime
        result = probe_training_runtime(FakeTorch())
        self.assertEqual(result["training_runtime"], "amd_rocm")
        self.assertIn("bf16", result["mixed_precision"])
        self.assertFalse(result["inference_supported"])
        self.assertEqual(result["total_device_memory_bytes"], 8 * 1024**3)

    def test_parameter_and_memory_estimates_are_positive_and_scale(self):
        from tools.train_mkaos_from_scratch import estimate_parameter_count, estimate_training_memory_bytes
        small = estimate_parameter_count(257, 32, 1, 4, 2, 64)
        larger = estimate_parameter_count(257, 2048, 24, 16, 4, 5504)
        self.assertGreater(small, 0)
        self.assertGreater(larger, small)
        small_memory = estimate_training_memory_bytes(small, 2, 64, 32, 1, 64)
        large_memory = estimate_training_memory_bytes(larger, 2, 512, 2048, 24, 5504)
        self.assertGreater(large_memory, small_memory)
        with self.assertRaises(ValueError):
            estimate_parameter_count(257, 30, 4, 4, 2, 64)


if __name__ == "__main__":
    unittest.main()
