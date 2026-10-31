from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

# The MCP server is an optional distribution. The dedicated developer-packages
# workflow installs it before running these tests; the core CI matrix should not
# fail merely because the optional package is intentionally absent.
if importlib.util.find_spec("mkaos_mcp_server") is None:
    raise unittest.SkipTest(
        "Optional MCP server is not installed; see packages/mkaos-mcp-server."
    )

from mkaos_mcp_server import server


class McpServerTests(unittest.TestCase):
    def test_reads_inside_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "hello.txt").write_text("hello MKAOS", encoding="utf-8")
            server._WORKSPACE = root.resolve()
            self.assertEqual(
                server._safe_file("hello.txt").read_text(encoding="utf-8"),
                "hello MKAOS",
            )

    def test_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            server._WORKSPACE = Path(directory).resolve()
            with self.assertRaises(ValueError):
                server._safe_file("../outside.txt")

    def test_rejects_hidden_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text("DO_NOT_READ", encoding="utf-8")
            server._WORKSPACE = root.resolve()
            with self.assertRaises(ValueError):
                server._safe_file(".env")


if __name__ == "__main__":
    unittest.main()
