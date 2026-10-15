"""Job-bus tenant isolation regression tests."""
import unittest
from core.job_bus import JobBus

class JobBusTenantIsolationTests(unittest.TestCase):
    def test_lists_and_get_are_scoped_to_owner(self):
        bus = JobBus()
        alice = bus.create("test", "Alice private job", owner_id="alice")
        bob = bus.create("test", "Bob private job", owner_id="bob")
        self.assertEqual([j["id"] for j in bus.list_recent(20, owner_id="alice")], [alice.id])
        self.assertEqual([j["id"] for j in bus.list_recent(20, owner_id="bob")], [bob.id])
        self.assertIsNone(bus.get(alice.id, owner_id="bob"))
        self.assertEqual(bus.get(alice.id, owner_id="alice")["title"], "Alice private job")

    def test_default_owner_cannot_list_other_tenant_jobs(self):
        bus = JobBus()
        bus.create("test", "private", owner_id="alice")
        self.assertEqual(bus.list_recent(owner_id="owner"), [])

if __name__ == "__main__":
    unittest.main()
