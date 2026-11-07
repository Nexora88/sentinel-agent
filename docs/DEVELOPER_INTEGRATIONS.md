# MKAOS developer integrations

All packages described here are alpha. Commands are source-checkout instructions, not evidence of a PyPI release.

## Independent MCP server

Install from the repository with `python -m pip install ./packages/mkaos-mcp-server`, then run `mkaos-mcp-server --workspace .`.

The official Python MCP SDK is used with stdio transport. The server exposes two read-only tools: `workspace_list(path='.')` (up to 200 visible entries) and `workspace_read_text(path)` (UTF-8 text files up to 128 KiB). Hidden files/directories, common secret filenames, databases, private keys, symlinks, and paths outside the configured workspace are excluded. There is no shell, network, or write tool.

### Claude Code example

`claude mcp add --transport stdio mkaos -- mkaos-mcp-server --workspace /absolute/path/to/project`

### Cursor example

Add `.cursor/mcp.json`:

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

Replace the sample path. These are configuration examples, not proof of successful desktop-client connections. Validate MCP initialization, tool listing, and a read operation in the installed client versions before claiming compatibility.

## Read-only CLI

Install with `python -m pip install -e .`. Run `mkaos scan .` or `mkaos scan . --json`. It performs bounded text-file reads, redacts matching evidence, and does not modify files. This heuristic is not a full SAST, dependency, malware, or compliance audit. Exit codes: 0 no heuristic match, 1 one or more matches, 2 invalid input/runtime error.

## Local REST API

Install API dependencies with `python -m pip install -e ".[api]"`. Set `MKAOS_API_TOKEN` to a random secret of at least 32 characters and optionally set `MKAOS_API_WORKSPACE` to the workspace root. Start with `mkaos api --host 127.0.0.1 --port 8765`.

The CLI refuses non-loopback binding. `POST /v1/scan` requires a Bearer token and confines the requested path to the configured root. Do not expose the development API directly to the public internet. A production deployment still needs HTTPS termination, rate limiting, audit logging, monitoring, and a deployment-specific threat review.

OpenAPI 3.1 schema: [../openapi/mkaos-openapi.yaml](../openapi/mkaos-openapi.yaml).

## PyPI release gate

Before publishing: test wheels in fresh virtual environments; run CI on Linux, Windows, and macOS; test MCP initialization and tool calls in actual Claude Code and Cursor clients; review metadata, license files, dependency licenses, and provenance; publish only reviewed, versioned artifacts.
