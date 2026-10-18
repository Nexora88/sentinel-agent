import unittest
from tools.mkaos_numerical_parity import compare_vectors

class NumericalParityTests(unittest.TestCase):
    def test_identical_vectors_pass_exactly(self):
        report = compare_vectors([0.25, -1.0, 3.0], [0.25, -1.0, 3.0])
        self.assertTrue(report["passed"])
        self.assertEqual(report["max_absolute_error"], 0.0)
        self.assertAlmostEqual(report["cosine_similarity"], 1.0)
    def test_small_rounding_error_passes_tolerance(self):
        report = compare_vectors([1.0, 2.0], [1.000001, 1.999999], atol=2e-6, rtol=0.0)
        self.assertTrue(report["passed"])
    def test_material_difference_fails_tolerance(self):
        report = compare_vectors([1.0, 2.0], [1.0, 2.1], atol=1e-5, rtol=1e-4)
        self.assertFalse(report["passed"])
    def test_mismatched_length_rejected(self):
        with self.assertRaises(ValueError):
            compare_vectors([1.0], [1.0, 2.0])
    def test_non_finite_values_rejected(self):
        with self.assertRaises(ValueError):
            compare_vectors([float("nan")], [0.0])

if __name__ == "__main__":
    unittest.main()
