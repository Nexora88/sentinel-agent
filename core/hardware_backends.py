"""Conservative hardware backend registry; discovery never implies validated support."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable


@dataclass(frozen=True)
class BackendStatus:
    name: str
    runtime: str
    status: str
    inference_supported: bool
    evidence: str
    next_validation: str


_BACKENDS = (
    ("cpu", "Ollama/llama.cpp or compatible local runtime",
     "available_as_fallback", True, "CPU execution is the conservative baseline.",
     "Measure latency, peak RSS, concurrency and Turkish task quality."),
    ("nvidia_cuda", "Ollama CUDA or vLLM CUDA",
     "not_probed", False, "No GPU/device probe has run in this process.",
     "Validate driver/runtime compatibility, VRAM, load test and numerical correctness."),
    ("amd_rocm", "ROCm-compatible Ollama or vLLM build",
     "not_probed", False, "Package presence alone is not device validation.",
     "Test exact GPU, kernel/driver, ROCm version, memory and sustained inference."),
    ("apple_metal", "Ollama/llama.cpp Metal",
     "not_probed", False, "Apple Silicon is not inferred from platform name alone.",
     "Test exact macOS/SoC, Metal runtime, unified memory and thermal throttling."),
    ("intel_gaudi", "Gaudi-compatible vLLM/runtime",
     "not_probed", False, "Requires a matching accelerator and vendor runtime.",
     "Validate HPU device, drivers, model operators and throughput."),
    ("npu_tpu", "Vendor-specific local runtime",
     "not_probed", False, "No universal NPU/TPU API is assumed.",
     "Add a vendor adapter and test on the exact supported device."),
)


def backend_registry() -> list[dict]:
    """Return honest capability metadata without network access or hardware claims."""
    return [asdict(BackendStatus(*item)) for item in _BACKENDS]


def probe_backend(name: str, probe: Callable[[], tuple[bool, str]]) -> dict:
    """Run an explicit caller-supplied local probe; never silently marks a backend supported."""
    known = {item[0]: item for item in _BACKENDS}
    if name not in known:
        raise ValueError("Unknown hardware backend.")
    item = known[name]
    try:
        passed, evidence = probe()
    except Exception as exc:
        passed, evidence = False, "Probe failed: " + type(exc).__name__
    status = "probe_passed_not_benchmarked" if passed else "probe_failed"
    return asdict(BackendStatus(item[0], item[1], status, False,
                                str(evidence)[:1000],
                                "A successful probe is not a performance benchmark or production certification."))
