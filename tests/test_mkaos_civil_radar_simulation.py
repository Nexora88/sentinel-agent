import unittest

from scripts.mkaos.civil_radar_simulation import (
    generate_synthetic_echoes,
    moving_average,
    summarize_signal,
)


class CivilRadarSimulationTests(unittest.TestCase):
    def test_seeded_signal_is_reproducible(self):
        self.assertEqual(generate_synthetic_echoes(seed=42), generate_synthetic_echoes(seed=42))

    def test_signal_length_and_finite_values(self):
        values = generate_synthetic_echoes(sample_count=64)
        self.assertEqual(len(values), 64)
        self.assertTrue(all(abs(value) < 2 for value in values))

    def test_filter_preserves_length(self):
        values = generate_synthetic_echoes(sample_count=64)
        self.assertEqual(len(moving_average(values, window=5)), len(values))

    def test_filter_rejects_invalid_window(self):
        with self.assertRaises(ValueError):
            moving_average([1.0, 2.0], window=3)

    def test_input_bounds(self):
        with self.assertRaises(ValueError):
            generate_synthetic_echoes(sample_count=8)
        with self.assertRaises(ValueError):
            generate_synthetic_echoes(noise_amplitude=float("nan"))

    def test_summary_labels_only_descriptive_statistics(self):
        report = summarize_signal([1.0, 2.0, 3.0])
        self.assertEqual(report["sample_count"], 3)
        self.assertEqual(report["minimum"], 1.0)
        self.assertEqual(report["maximum"], 3.0)
        self.assertEqual(report["mean"], 2.0)


if __name__ == "__main__":
    unittest.main()
