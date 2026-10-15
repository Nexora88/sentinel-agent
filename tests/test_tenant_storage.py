"""Regression tests for tenant storage boundaries."""
import tempfile
import unittest
from core.tenant_storage import tenant_file, tenant_root, tenant_storage_id

class TenantStorageTests(unittest.TestCase):
    def test_each_user_gets_a_distinct_root_and_file(self):
        with tempfile.TemporaryDirectory() as temp:
            alice = tenant_file(temp, "alice", "notes.txt")
            bob = tenant_file(temp, "bob", "notes.txt")
            self.assertNotEqual(alice, bob)
            alice.parent.mkdir(parents=True)
            bob.parent.mkdir(parents=True)
            alice.write_text("alice private", encoding="utf-8")
            bob.write_text("bob private", encoding="utf-8")
            self.assertEqual(alice.read_text(encoding="utf-8"), "alice private")
            self.assertEqual(bob.read_text(encoding="utf-8"), "bob private")

    def test_rejects_path_traversal_and_unsafe_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            for identity in ("../owner", "..", "", "x/y", "user with spaces"):
                with self.subTest(identity=identity), self.assertRaises(ValueError):
                    tenant_root(temp, identity)
            for filename in ("../secret.txt", "/tmp/secret.txt", "", ".."):
                with self.subTest(filename=filename), self.assertRaises(ValueError):
                    tenant_file(temp, "alice", filename)

    def test_username_storage_keys_are_safe_and_stable(self):
        self.assertEqual(tenant_storage_id("Alice@Example.com"), tenant_storage_id("alice@example.com"))
        self.assertNotEqual(tenant_storage_id("alice@example.com"), tenant_storage_id("bob@example.com"))
        self.assertRegex(tenant_storage_id("Alice@Example.com"), r"^u-[a-f0-9]{32}$")

    def test_case_normalization_is_stable(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(tenant_root(temp, "Alice"), tenant_root(temp, "alice"))

if __name__ == "__main__":
    unittest.main()
