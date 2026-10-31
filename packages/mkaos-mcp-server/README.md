# mkaos-mcp-server

Independent Python distribution providing a **read-only stdio MCP server** for a selected workspace.

## Install from a source checkout

```bash
python -m pip install ./packages/mkaos-mcp-server
mkaos-mcp-server --workspace .
```

Or install from PyPI after a maintainer publishes a reviewed release:

```bash
python -m pip install mkaos-mcp-server
```

## Exposed tools

- `workspace_list(path=".")`: lists up to 200 non-hidden entries.
- `workspace_read_text(path)`: reads a UTF-8 text file up to 128 KiB.

The server does not expose shell execution, writes, arbitrary network access, hidden files, common secret files, database files, or symlink targets. It is a bounded convenience layer, not a complete security boundary. Run it only in a workspace you are authorized to inspect.

## Claude Code

```bash
claude mcp add --transport stdio mkaos -- mkaos-mcp-server --workspace /absolute/path/to/project
```

## Cursor

Add to the project's `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "mkaos": {
      "command": "mkaos-mcp-server",
      "args": ["--workspace", "/absolute/path/to/project"]
    }
  }
}
```

Replace the example path with your own workspace path. These are configuration examples; compatibility must be confirmed with the installed client versions.
