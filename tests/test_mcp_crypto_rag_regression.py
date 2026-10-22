"""Focused regression checks for encrypted RAG and MCP input boundaries."""
import base64
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.crypto_rag import CryptoRAGError, EncryptedVectorStore
from core.mcp_server import handle_message


class CryptoRAGRegressionTests(unittest.TestCase):
    def test_batch_validation_is_atomic_and_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vectors.sqlite3"
            store = EncryptedVectorStore(path, b"r" * 32)
            with self.assertRaises(CryptoRAGError):
                store.upsert_many([
                    {"record_id": "ok", "embedding": [1.0, 0.0], "document": "first"},
                    {"record_id": "bad", "embedding": [float("nan")], "document": "second"},
                ])
            self.assertEqual(store.count(), 0)
            store.upsert_many([
                {"record_id": "opaque-1", "embedding": [1.0, 0.0], "document": "private alpha"},
                {"record_id": "opaque-2", "embedding": [0.0, 1.0], "document": "private beta"},
            ])
            reopened = EncryptedVectorStore(path, b"r" * 32)
            self.assertEqual(reopened.count(), 2)
            self.assertEqual(reopened.get("opaque-1")["document"], "private alpha")

    def test_search_authentication_fails_closed_for_wrong_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vectors.sqlite3"
            EncryptedVectorStore(path, b"a" * 32).upsert(
                record_id="opaque", embedding=[1.0, 0.0], document="confidential"
            )
            with self.assertRaises(CryptoRAGError):
                EncryptedVectorStore(path, b"b" * 32).search([1.0, 0.0])

    def test_database_and_wal_sidecars_do_not_contain_plaintext(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "vectors.sqlite3"
            store = EncryptedVectorStore(path, b"z" * 32)
            store.upsert(
                record_id="opaque-random-id",
                embedding=[0.25, 0.75],
                document="confidential marker 7e6b1d",
                metadata={"source": "private/source/path"},
            )
            # SQLite may checkpoint/remove WAL files on close; inspect every extant file.
            for candidate in Path(tmp).rglob("*"):
                if candidate.is_file():
                    raw = candidate.read_bytes()
                    self.assertNotIn(b"confidential marker 7e6b1d", raw)
                    self.assertNotIn(b"private/source/path", raw)

    def test_mcp_rejects_non_object_tool_arguments_and_unknown_tools(self):
        malformed = handle_message({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "workspace_read_text", "arguments": "docs/README.md"},
        })
        self.assertEqual(malformed["error"]["code"], -32602)
        unknown = handle_message({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "execute_shell", "arguments": {}},
        })
        self.assertEqual(unknown["error"]["code"], -32602)

    def test_mcp_rejects_paths_outside_allowlisted_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"MKAOS_MCP_WORKSPACE": tmp}):
                for path in ("/etc/passwd", "../docs/secret.md", "memory/private.db", "docs/../.env"):
                    response = handle_message({
                        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                        "params": {"name": "workspace_read_text", "arguments": {"path": path}},
                    })
                    self.assertTrue(response["result"]["isError"], path)


if __name__ == "__main__":
    unittest.main()
