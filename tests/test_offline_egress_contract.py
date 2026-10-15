"""Contract tests for validator metadata; no network probes run in unit CI."""
import unittest
from scripts.validate_offline_egress import TARGETS

class OfflineEgressContractTests(unittest.TestCase):
    def test_targets_are_fixed_public_ip_ports(self):
        self.assertEqual(TARGETS, [("1.1.1.1", 443), ("8.8.8.8", 53), ("9.9.9.9", 443)])
        self.assertTrue(all(isinstance(port, int) for _, port in TARGETS))

if __name__ == "__main__": unittest.main()
