"""Portable, offline platform profile for MKAOS.

This module reports the host's basic runtime identity only. It does not infer
accelerator support, model compatibility, or production readiness from OS names.
"""
from __future__ import annotations

import platform
import sys
from typing import Any


_OS_ALIASES = {
    "windows": "windows",
    "linux": "linux",
    "darwin": "macos",
}
_ARCH_ALIASES = {
    "x86_64": "x86_64",
    "amd64": "x86_64",
    "aarch64": "aarch64",
    "arm64": "aarch64",
    "i386": "x86",
    "i686": "x86",
    "x86": "x86",
}


def get_platform_profile() -> dict[str, Any]:
    """Return deterministic, privacy-minimal host metadata without network access."""
    raw_os = platform.system().strip().lower()
    raw_arch = platform.machine().strip().lower()
    os_name = _OS_ALIASES.get(raw_os, "other")
    architecture = _ARCH_ALIASES.get(raw_arch, "other")
    return {
        "schema_version": 1,
        "os": os_name,
        "architecture": architecture,
        "python": {
            "implementation": platform.python_implementation(),
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        },
        "cpu_baseline": "available",
        "accelerators": {
            "nvidia_cuda": "not_probed",
            "amd_rocm": "not_probed",
            "apple_metal": "not_probed",
            "intel_gaudi": "not_probed",
            "npu_tpu": "not_probed",
        },
        "network_accessed": False,
        "model_compatibility": "not_assessed",
        "performance_benchmarked": False,
    }
