"""
Local network discovery — READ ONLY.
Lists common open ports on localhost / optional CIDR.
Does NOT control cameras, IoT actuators, or change device config.
"""

from __future__ import annotations

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

COMMON_PORTS = [
    22, 80, 443, 445, 1883, 5353, 8000, 8080, 8443, 9000, 9100, 11434
]


def _probe(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


class LocalDiscovery:
    def scan_localhost(self) -> Dict:
        open_ports: List[int] = []
        with ThreadPoolExecutor(max_workers=16) as ex:
            futs = {ex.submit(_probe, "127.0.0.1", p): p for p in COMMON_PORTS}
            for fut in as_completed(futs):
                if fut.result():
                    open_ports.append(futs[fut])
        open_ports.sort()
        return {
            "host": "127.0.0.1",
            "open_ports": open_ports,
            "notes": [
                "Read-only scan. No credentials used. No device control.",
                "Ollama often on 11434; web UI often on 8000.",
            ],
        }

    def format_report(self, result: Dict) -> str:
        ports = ", ".join(str(p) for p in result.get("open_ports", [])) or "(none)"
        lines = [
            "🔌 Local discovery (read-only)",
            f"Host: {result.get('host')}",
            f"Open common ports: {ports}",
        ]
        lines.extend(f"  • {n}" for n in result.get("notes", []))
        return "\n".join(lines)
