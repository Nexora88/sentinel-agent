import unittest

from tools.benchmark_mkaos_vs_ollama import parse_memory_mb


class MkaosBenchmarkMemoryParsingTests(unittest.TestCase):
    def test_parses_docker_mib_and_gib_values(self):
        self.assertAlmostEqual(parse_memory_mb("123.4MiB / 7.6GiB"), 123.4)
        self.assertAlmostEqual(parse_memory_mb("1.5GiB"), 1536.0)

    def test_parses_ps_rss_as_kib_when_no_unit_is_given(self):
        self.assertAlmostEqual(parse_memory_mb("102400"), 100.0)

    def test_invalid_memory_value_is_ignored(self):
        self.assertIsNone(parse_memory_mb("not available"))


if __name__ == "__main__":
    unittest.main()
