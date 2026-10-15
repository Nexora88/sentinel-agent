"""Linux network-namespace egress test. It never edits host firewall rules."""
from __future__ import annotations
import argparse, json, platform, shutil, socket, subprocess, sys
TARGETS = [("1.1.1.1", 443), ("8.8.8.8", 53), ("9.9.9.9", 443)]

def probe() -> dict:
    results = []
    for host, port in TARGETS:
        try:
            with socket.create_connection((host, port), timeout=2):
                results.append({"target": f"{host}:{port}", "blocked": False, "error": None})
        except OSError as exc:
            results.append({"target": f"{host}:{port}", "blocked": True, "error": type(exc).__name__})
    return {"mode": "linux_network_namespace", "probes": results,
            "pass": all(row["blocked"] for row in results),
            "claim_limit": "Only this isolated namespace was tested; parent-host egress and packet capture are not proven."}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inside-netns", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if platform.system() != "Linux":
        print(json.dumps({"pass": False, "reason": "Linux network namespace required."}, indent=2)); return 2
    if args.inside_netns:
        report = probe()
    else:
        unshare = shutil.which("unshare")
        if not unshare:
            print(json.dumps({"pass": False, "reason": "unshare is not installed; no test performed."}, indent=2)); return 2
        child = subprocess.run([unshare, "--net", "--", sys.executable, __file__, "--inside-netns"],
                               capture_output=True, text=True, timeout=20, check=False)
        if child.returncode:
            print(json.dumps({"pass": False, "reason": "Namespace creation failed; likely insufficient capability.",
                              "stderr": child.stderr[-1000:], "no_host_firewall_changes": True}, indent=2)); return 2
        try: report = json.loads(child.stdout)
        except ValueError:
            print(json.dumps({"pass": False, "reason": "Child returned invalid report."}, indent=2)); return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1

if __name__ == "__main__": raise SystemExit(main())
