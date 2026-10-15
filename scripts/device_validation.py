"""Portable MKAOS device/provenance report; diagnostic only, never a pass claim.
Usage: python scripts/device_validation.py [--model-file /path/to/weights]
"""
from __future__ import annotations
import argparse, hashlib, json, os, platform, shutil, subprocess, sys
from pathlib import Path

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()

def command_version(command: list[str]) -> dict:
    executable = shutil.which(command[0])
    if not executable: return {"available": False, "version": None}
    try:
        result = subprocess.run([executable, *command[1:]], capture_output=True, text=True, timeout=4, check=False)
        output = (result.stdout or result.stderr).strip().splitlines()
        return {"available": result.returncode == 0, "version": output[0][:240] if output else None, "return_code": result.returncode}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": type(exc).__name__}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-file", action="append", default=[], help="Local model/weight file; may be repeated")
    args = parser.parse_args()
    report = {
        "report_version": 1, "purpose": "diagnostic_only",
        "device": {"os": platform.system(), "os_release": platform.release(), "architecture": platform.machine(), "python": sys.version.split()[0], "android_client_separate_from_model": "not_tested_by_this_script"},
        "runtime": {
            "ollama": command_version(["ollama", "--version"]),
            "nvidia_smi": command_version(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"]),
            "rocm_smi": command_version(["rocm-smi", "--showproductname"]),
            "system_profiler": command_version(["system_profiler", "SPDisplaysDataType"]),
        },
        "model_files": [], "environment": {"CI": os.getenv("CI", "false")},
        "limitations": ["A CLI being present does not prove GPU execution or model correctness.", "Android client tests and Android local-model tests are separate test plans.", "CPU/NVIDIA/AMD/Apple GPU validation requires actual target hardware and recorded inference.", "Model origin and license must be checked against upstream documentation separately."]
    }
    for raw in args.model_file:
        path = Path(raw).expanduser()
        entry = {"path": str(path), "exists": path.is_file()}
        if path.is_file(): entry.update({"size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
        report["model_files"].append(entry)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__": raise SystemExit(main())
