"""Read-only MCP server with explicit workspace confinement."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MKAOS Read-only Workspace")
_WORKSPACE = Path(os.environ.get("MKAOS_MCP_WORKSPACE", ".")).expanduser().resolve()
MAX_READ_BYTES = 128 * 1024
BLOCKED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".ssh", ".aws"}
BLOCKED_NAMES = {".env", ".env.local", ".env.production", "credentials.json", "secrets.json", "id_rsa", "id_ed25519"}

def _safe_file(relative_path: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path or len(relative_path) > 512:
        raise ValueError("A bounded relative path is required.")
    raw = Path(relative_path)
    if raw.is_absolute() or any(part in {"..", ""} for part in raw.parts):
        raise ValueError("Absolute paths and traversal are not allowed.")
    if any(part.lower() in BLOCKED_DIRS for part in raw.parts):
        raise ValueError("This directory is excluded from MCP access.")
    name = raw.name.lower()
    if name in BLOCKED_NAMES or name.startswith(".env") or name.endswith((".pem", ".key", ".p12", ".pfx", ".db", ".sqlite", ".sqlite3")):
        raise ValueError("Secret and private data files are not exposed.")
    cursor = _WORKSPACE
    for part in raw.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlink paths are not exposed.")
    resolved = cursor.resolve(strict=True)
    if not resolved.is_relative_to(_WORKSPACE) or not resolved.is_file():
        raise ValueError("Path is outside the workspace or is not a file.")
    if resolved.stat().st_size > MAX_READ_BYTES:
        raise ValueError("File exceeds the 128 KiB read limit.")
    return resolved

@mcp.tool()
def workspace_list(path: str = ".") -> list[dict[str, str]]:
    """List up to 200 non-hidden, non-secret entries in a workspace directory."""
    relative = Path(path)
    if relative.is_absolute() or any(part == ".." for part in relative.parts):
        raise ValueError("Invalid relative directory.")
    target = (_WORKSPACE / relative).resolve(strict=True)
    if not target.is_relative_to(_WORKSPACE) or not target.is_dir():
        raise ValueError("Directory is outside the workspace.")
    results = []
    for child in sorted(target.iterdir(), key=lambda p: p.name.lower()):
        if child.is_symlink() or child.name.startswith(".") or child.name.lower() in BLOCKED_DIRS | BLOCKED_NAMES:
            continue
        results.append({"name": child.name, "type": "directory" if child.is_dir() else "file"})
        if len(results) >= 200:
            break
    return results

@mcp.tool()
def workspace_read_text(path: str) -> str:
    """Read one bounded UTF-8 text file inside the configured workspace; read-only."""
    return _safe_file(path).read_text(encoding="utf-8")

def run_server(workspace: str = ".") -> None:
    global _WORKSPACE
    _WORKSPACE = Path(workspace).expanduser().resolve(strict=True)
    if not _WORKSPACE.is_dir():
        raise ValueError("Workspace must be a directory.")
    mcp.run(transport="stdio")

def main() -> None:
    parser = argparse.ArgumentParser(prog="mkaos-mcp-server", description="Read-only MKAOS MCP server")
    parser.add_argument("--workspace", default=os.environ.get("MKAOS_MCP_WORKSPACE", "."))
    args = parser.parse_args()
    run_server(args.workspace)

if __name__ == "__main__":
    main()
