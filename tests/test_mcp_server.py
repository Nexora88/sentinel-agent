import os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from core.mcp_server import handle_message, read_workspace_text

class MCPServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "safe.md").write_text("MKAOS docs", encoding="utf-8")
        (self.root / "docs" / ".env").write_text("TOKEN=secret", encoding="utf-8")
        self.patch = patch.dict(os.environ, {"MKAOS_MCP_WORKSPACE": str(self.root)})
        self.patch.start()
    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()
    def test_read_allowlisted_file(self):
        self.assertEqual(read_workspace_text("docs/safe.md"), "MKAOS docs")
    def test_reject_traversal_and_secret_files(self):
        for value in ("../docs/safe.md", "/etc/passwd", "docs/.env", "secrets/keys.pem"):
            with self.subTest(value=value), self.assertRaises(ValueError): read_workspace_text(value)
    def test_tools_list_and_invalid_method(self):
        result = handle_message({"jsonrpc":"2.0","id":1,"method":"tools/list"})
        self.assertEqual(result["result"]["tools"][0]["name"], "workspace_read_text")
        result = handle_message({"jsonrpc":"2.0","id":2,"method":"nope"})
        self.assertEqual(result["error"]["code"], -32601)
    def test_tools_call_returns_error_content(self):
        result = handle_message({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"workspace_read_text","arguments":{"path":"../secret"}}})
        self.assertTrue(result["result"]["isError"])

if __name__ == "__main__": unittest.main()
