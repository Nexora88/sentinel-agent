#!/usr/bin/env python3
"""Low-resource, offline MKAOS setup preflight.

This command only inspects local machine/runtime configuration. It never downloads
models, contacts a service, starts inference, or changes training approval gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _available_ram_bytes() -> int | None:
    """Return available RAM where a standard-library implementation is available."""
    if sys.platform.startswith("linux"):
        try:
            for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
        except (OSError, ValueError, IndexError):
            return None
    if sys.platform == "win32":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullAvailPhys)
        except (AttributeError, OSError, TypeError):
            return None
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _version(command: str) -> dict[str, Any]:
    executable = shutil.which(command)
    if not executable:
        return {"available": False, "path": None, "version": None}
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            shell=False,
        )
        version = (result.stdout or result.stderr).strip().splitlines()
        return {
            "available": result.returncode == 0,
            "path": executable,
            "version": version[0] if version else None,
        }
    except (OSError, subprocess.SubprocessError):
        return {"available": False, "path": executable, "version": None}


def build_report(repo_root: Path, min_free_gb: float = 5.0) -> dict[str, Any]:
    root = repo_root.resolve()
    disk = shutil.disk_usage(root)
    available_ram = _available_ram_bytes()
    checkpoint_raw = os.environ.get("MKAOS_NATIVE_CHECKPOINT", "").strip()
    expected_hash = os.environ.get("MKAOS_NATIVE_SHA256", "").strip().lower()
    generator_raw = os.environ.get("MKAOS_NATIVE_GENERATOR", "").strip()
    checkpoint: dict[str, Any] = {
        "configured": bool(checkpoint_raw),
        "exists": False,
        "sha256_verified": False,
        "message": "No local checkpoint configured; no model was downloaded.",
    }
    if checkpoint_raw:
        path = Path(checkpoint_raw).expanduser()
        if path.is_file():
            checkpoint["exists"] = True
            if len(expected_hash) == 64 and all(c in "0123456789abcdef" for c in expected_hash):
                actual = _sha256(path)
                checkpoint["sha256_verified"] = actual == expected_hash
                checkpoint["message"] = (
                    "Checkpoint SHA-256 matches the configured digest."
                    if actual == expected_hash
                    else "Checkpoint SHA-256 mismatch."
                )
            else:
                checkpoint["message"] = "Checkpoint exists, but a valid MKAOS_NATIVE_SHA256 is not configured."
        else:
            checkpoint["message"] = "Configured checkpoint path does not exist."

    generator = Path(generator_raw).expanduser() if generator_raw else None
    report = {
        "report_version": 1,
        "mode": "read-only-local-preflight",
        "network_used": False,
        "inference_started": False,
        "training_started": False,
        "repo_root": str(root),
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "disk": {
            "free_bytes": disk.free,
            "free_gib": round(disk.free / (1024 ** 3), 2),
            "minimum_recommended_gib": min_free_gb,
            "sufficient_for_preflight": disk.free >= min_free_gb * (1024 ** 3),
        },
        "memory": {
            "available_bytes": available_ram,
            "available_gib": round(available_ram / (1024 ** 3), 2) if available_ram is not None else None,
            "note": "Available RAM is a point-in-time estimate; model memory must be measured during a real run.",
        },
        "runtime": {"rustc": _version("rustc"), "cargo": _version("cargo")},
        "native_generator": {
            "configured": bool(generator_raw),
            "exists": bool(generator and generator.is_file()),
            "path": str(generator) if generator else None,
        },
        "checkpoint": checkpoint,
        "training_gate": "UNCHANGED — this preflight cannot approve data or enable training",
        "notes": [
            "No model weights or datasets were downloaded.",
            "A successful preflight does not prove Turkish quality, speed, privacy isolation, or model compatibility.",
            "If checkpoint or generator is missing, fix that explicitly; do not silently fall back to a hosted model.",
        ],
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--min-free-gb", type=float, default=5.0)
    args = parser.parse_args(argv)
    if args.min_free_gb < 0:
        parser.error("--min-free-gb must be non-negative")
    print(json.dumps(build_report(args.repo_root, args.min_free_gb), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
