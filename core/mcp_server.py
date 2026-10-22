"""Minimal read-only MCP stdio server for allowlisted workspace files.

No network listener, shell, file writes, arbitrary paths, or remote discovery.
Run with: python -m core.mcp_server
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from typing import Any

MAX_LINE_BYTES = 1024 * 1024
MAX_READ_BYTES = 128 * 1024
_ALLOWED_ROOTS = ("docs", "core", "agents", "tools", "tests", "config")
_BLOCKED_PARTS = {".git", "__pycache__", "node_modules", ".venv", "venv"}
_BLOCKED_NAMES = {".env", ".env.local", ".env.production", "secrets.json", "credentials.json"}

def _workspace() -> Path:
    return Path(os.environ.get("MKAOS_MCP_WORKSPACE", ".")).resolve()

def read_workspace_text(relative_path: str) -> str:
    if not isinstance(relative_path, str) or not relative_path or len(relative_path) > 512:
        raise ValueError("A bounded relative path is required.")
    candidate_path = Path(relative_path)
    if candidate_path.is_absolute() or any(part in ("..", "") for part in candidate_path.parts):
        raise ValueError("Path traversal and absolute paths are not allowed.")
    if candidate_path.parts[0] not in _ALLOWED_ROOTS:
        raise ValueError("Path is outside the MCP read-only allowlist.")
    if any(part in _BLOCKED_PARTS for part in candidate_path.parts):
        raise ValueError("Path contains a blocked directory.")
    if candidate_path.name.lower() in _BLOCKED_NAMES or candidate_path.name.lower().endswith((".pem", ".key", ".p12", ".pfx")):
        raise ValueError("Secret and private-key files are not exposed over MCP.")
    root = _workspace()
    cursor = root
    for part in candidate_path.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlink paths are not exposed over MCP.")
    resolved = (root / candidate_path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Resolved path escapes the workspace.")
    if not resolved.is_file() or resolved.stat().st_size > MAX_READ_BYTES:
        raise ValueError("File is missing or exceeds the read limit.")
    return resolved.read_text(encoding="utf-8")

def _response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}

def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

def handle_message(message: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _error(message.get("id") if isinstance(message, dict) else None, -32600, "Invalid JSON-RPC request.")
    method, request_id = message.get("method"), message.get("id")
    params = message.get("params") or {}
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return _response(request_id, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "mkaos-readonly-workspace", "version": "0.1.0"}})
    if method == "ping":
        return _response(request_id, {})
    if method == "tools/list":
        return _response(request_id, {"tools": [{"name": "workspace_read_text", "description": "Read a bounded UTF-8 file from allowlisted project folders. Read-only; no secrets.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}}]})
    if method == "tools/call":
        if not isinstance(params, dict) or params.get("name") != "workspace_read_text":
            return _error(request_id, -32602, "Unknown tool.")
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict) or set(arguments) != {"path"}:
            return _error(request_id, -32602, "Expected only the path argument.")
        try:
            content = read_workspace_text(arguments["path"])
            return _response(request_id, {"content": [{"type": "text", "text": content}], "isError": False})
        except (ValueError, OSError, UnicodeError) as exc:
            return _response(request_id, {"content": [{"type": "text", "text": str(exc)}], "isError": True})
    return _error(request_id, -32601, "Method not found.")

def main() -> int:
    # stdout is reserved exclusively for MCP protocol messages.
    while True:
        line = sys.stdin.buffer.readline(MAX_LINE_BYTES + 1)
        if not line:
            return 0
        if len(line) > MAX_LINE_BYTES:
            response = _error(None, -32700, "Request exceeds 1 MiB.")
        else:
            try:
                response = handle_message(json.loads(line))
            except (json.JSONDecodeError, UnicodeError):
                response = _error(None, -32700, "Parse error.")
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    raise SystemExit(main())
