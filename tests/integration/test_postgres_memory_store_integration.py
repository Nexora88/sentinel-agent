"""Live PostgreSQL integration tests. Run only against a disposable test database.

The connection must use a non-superuser, non-BYPASSRLS application role.
Apply deploy/postgres/001_mkaos_encrypted_sessions.sql before running.
"""
from __future__ import annotations

import os
import unittest
import uuid

from core.postgres_memory_store import PostgresMemoryStore

DSN = os.getenv("MKAOS_TEST_POSTGRES_DSN")
KEY = os.getenv("MKAOS_MEMORY_ENCRYPTION_KEY")


@unittest.skipUnless(DSN and KEY, "set MKAOS_TEST_POSTGRES_DSN and MKAOS_MEMORY_ENCRYPTION_KEY for live PostgreSQL tests")
class PostgresMemoryStoreIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.store = PostgresMemoryStore(dsn=DSN, encryption_key=KEY)
        self.tenant_a = "it-a-" + uuid.uuid4().hex
        self.tenant_b = "it-b-" + uuid.uuid4().hex
        self.session_a = self.store.create_session(self.tenant_a, {"purpose": "integration"})
        self.session_b = self.store.create_session(self.tenant_b, {"purpose": "integration"})

    def tearDown(self):
        try:
            with self.store.connection.transaction():
                with self.store.connection.cursor() as cur:
                    for tenant in (self.tenant_a, self.tenant_b):
                        cur.execute("SELECT set_config('mkaos.tenant_id', %s, true)", (tenant,))
                        cur.execute("DELETE FROM mkaos_messages WHERE tenant_id = %s", (tenant,))
                        cur.execute("DELETE FROM mkaos_memories WHERE tenant_id = %s", (tenant,))
                        cur.execute("DELETE FROM mkaos_sessions WHERE tenant_id = %s", (tenant,))
        finally:
            self.store.close()

    def test_session_message_and_memory_round_trip_are_encrypted_and_tenant_scoped(self):
        secret_message = "gizli entegrasyon mesajı " + uuid.uuid4().hex
        self.store.append_message(self.tenant_a, self.session_a, "user", secret_message)
        self.assertEqual(self.store.list_messages(self.tenant_a, self.session_a)[0]["content"], secret_message)
        self.assertEqual(self.store.list_messages(self.tenant_b, self.session_a), [])

        memory_id = self.store.put_memory(self.tenant_a, {"fact": "özel not"}, memory_kind="fact")
        self.assertEqual(self.store.list_memories(self.tenant_a)[0]["payload"], {"fact": "özel not"})
        self.assertEqual(self.store.list_memories(self.tenant_b), [])

        with self.store.connection.transaction():
            with self.store.connection.cursor() as cur:
                cur.execute("SELECT set_config('mkaos.tenant_id', %s, true)", (self.tenant_a,))
                cur.execute("SELECT content_ciphertext FROM mkaos_messages WHERE tenant_id = %s", (self.tenant_a,))
                ciphertext = bytes(cur.fetchone()[0])
                self.assertNotIn(secret_message.encode("utf-8"), ciphertext)
                cur.execute("SELECT id FROM mkaos_memories WHERE id = %s", (memory_id,))
                self.assertIsNotNone(cur.fetchone())

    def test_database_rls_hides_other_tenant_rows_even_without_application_filter(self):
        with self.store.connection.transaction():
            with self.store.connection.cursor() as cur:
                cur.execute("SELECT set_config('mkaos.tenant_id', %s, true)", (self.tenant_a,))
                cur.execute("SELECT id FROM mkaos_sessions")
                visible = {str(row[0]) for row in cur.fetchall()}
                self.assertIn(self.session_a, visible)
                self.assertNotIn(self.session_b, visible)

    def test_cross_tenant_session_write_is_rejected(self):
        with self.assertRaises(LookupError):
            self.store.append_message(self.tenant_a, self.session_b, "user", "must not cross tenants")


if __name__ == "__main__":
    unittest.main()
