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
        for value in ("../docs/safe.md", ".", "/etc/passwd", "docs/.env", "docs/.env.development", "docs/secrets.yaml", "docs/id_ed25519", "docs/state.sqlite3", "docs/api_key.json", "docs/access_token.txt", "secrets/keys.pem"):
            with self.subTest(value=value), self.assertRaises(ValueError): read_workspace_text(value)
    def test_tools_list_and_invalid_method(self):
        result = handle_message({"jsonrpc":"2.0","id":1,"method":"tools/list"})
        self.assertEqual(result["result"]["tools"][0]["name"], "workspace_read_text")
        result = handle_message({"jsonrpc":"2.0","id":2,"method":"nope"})
        self.assertEqual(result["error"]["code"], -32601)
    def test_symlink_escape_is_rejected(self):
        outside = self.root.parent / (self.root.name + "-outside.txt")
        outside.write_text("not for MCP", encoding="utf-8")
        link = self.root / "docs" / "linked.txt"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            outside.unlink(missing_ok=True)
            self.skipTest("Symlink creation is unavailable on this runner.")
        try:
            with self.assertRaises(ValueError):
                read_workspace_text("docs/linked.txt")
        finally:
            outside.unlink(missing_ok=True)

    def test_tools_call_rejects_malformed_params(self):
        result = handle_message({"jsonrpc":"2.0","id":3,"method":"tools/call","params":"not-an-object"})
        self.assertEqual(result["error"]["code"], -32602)

    def test_tools_call_returns_error_content(self):
        result = handle_message({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"workspace_read_text","arguments":{"path":"../secret"}}})
        self.assertTrue(result["result"]["isError"])

if __name__ == "__main__": unittest.main()
