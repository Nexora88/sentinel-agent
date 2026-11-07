"""Command-line entry point for MKAOS."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .scanner import scan_workspace

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mkaos", description="MKAOS local-first developer tools")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="Read-only local workspace scan")
    scan.add_argument("path", nargs="?", default=".", help="Directory to scan (default: current directory)")
    scan.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    scan.add_argument("--max-files", type=int, default=10_000)
    mcp = sub.add_parser("mcp", help="Launch the optional read-only MCP server over stdio")
    mcp.add_argument("--workspace", default=".")
    api = sub.add_parser("api", help="Launch the optional token-protected local REST API")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if args.command == "scan":
        try:
            report = scan_workspace(args.path, max_files=args.max_files)
        except (OSError, ValueError) as exc:
            print(f"mkaos: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"MKAOS read-only scan · {report['target']}")
            print(f"Files scanned: {report['files_scanned']} · skipped: {report['files_skipped']}")
            for finding in report["findings"]:
                print(f"[{finding['severity'].upper()}] {finding['path']}:{finding['line']} · {finding['rule']} · evidence redacted")
            if not report["findings"]:
                print("No heuristic matches found.")
            if report["truncated"]:
                print("Scan limit reached; results are incomplete.")
            print(report["disclaimer"])
        return 1 if report["findings"] else 0
    if args.command == "mcp":
        try:
            from mkaos_mcp_server.server import run_server
        except ImportError:
            print("Install MCP support with: python -m pip install 'mkaos[mcp]'", file=sys.stderr)
            return 2
        run_server(args.workspace)
        return 0
    if args.command == "api":
        try:
            import uvicorn
            from .api import app
        except ImportError:
            print("Install API support with: python -m pip install 'mkaos[api]'", file=sys.stderr)
            return 2
        if args.host not in {"127.0.0.1", "localhost", "::1"}:
            print("Remote binding is disabled by this CLI. Use a trusted HTTPS reverse proxy and review the security guide.", file=sys.stderr)
            return 2
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
        return 0
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
