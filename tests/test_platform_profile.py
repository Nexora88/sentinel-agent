"""Tests for portable host profiling; intentionally make no accelerator claims."""
from __future__ import annotations

import platform
import sys

from core.platform_profile import get_platform_profile


def test_profile_is_offline_and_does_not_claim_accelerator_support() -> None:
    profile = get_platform_profile()
    assert profile["schema_version"] == 1
    assert profile["network_accessed"] is False
    assert profile["performance_benchmarked"] is False
    assert profile["model_compatibility"] == "not_assessed"
    assert profile["cpu_baseline"] == "available"
    assert all(value == "not_probed" for value in profile["accelerators"].values())


def test_profile_reports_normalized_host_identity() -> None:
    profile = get_platform_profile()
    expected_os = {
        "Windows": "windows",
        "Linux": "linux",
        "Darwin": "macos",
    }.get(platform.system(), "other")
    expected_arch = {
        "x86_64": "x86_64",
        "AMD64": "x86_64",
        "aarch64": "aarch64",
        "arm64": "aarch64",
        "i386": "x86",
        "i686": "x86",
        "x86": "x86",
    }.get(platform.machine(), "other")
    assert profile["os"] == expected_os
    assert profile["architecture"] == expected_arch
    assert profile["python"]["implementation"] == platform.python_implementation()
    assert profile["python"]["version"] == (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
