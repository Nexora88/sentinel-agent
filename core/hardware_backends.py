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


def probe_training_runtime(torch_module=None) -> dict:
    """Inspect locally installed PyTorch training runtimes without network access.

    A detected accelerator means PyTorch can see it; it does not certify the
    Rust inference engine, model operators, numerical parity, or performance.
    """
    try:
        if torch_module is None:
            import torch as torch_module
    except ImportError:
        return {
            "pytorch_available": False,
            "training_runtime": None,
            "device_name": None,
            "device_count": 0,
            "mixed_precision": [],
            "inference_supported": False,
            "evidence": "PyTorch is not installed in this Python environment.",
        }

    try:
        cuda_available = bool(torch_module.cuda.is_available())
    except Exception:
        cuda_available = False
    if cuda_available:
        try:
            is_rocm = bool(getattr(getattr(torch_module, "version", None), "hip", None))
            device_name = str(torch_module.cuda.get_device_name(0))
            device_count = int(torch_module.cuda.device_count())
            properties = torch_module.cuda.get_device_properties(0)
            total_memory = int(getattr(properties, "total_memory", 0) or 0)
            bf16 = bool(
                hasattr(torch_module.cuda, "is_bf16_supported")
                and torch_module.cuda.is_bf16_supported()
            )
            return {
                "pytorch_available": True,
                "training_runtime": "amd_rocm" if is_rocm else "nvidia_cuda",
                "device_name": device_name,
                "device_count": device_count,
                "total_device_memory_bytes": total_memory or None,
                "mixed_precision": ["fp32", "fp16"] + (["bf16"] if bf16 else []),
                "inference_supported": False,
                "evidence": "PyTorch accelerator runtime detected locally; Rust inference support and benchmarks remain unverified.",
            }
        except Exception as exc:
            return {
                "pytorch_available": True,
                "training_runtime": "cuda_api_probe_failed",
                "device_name": None,
                "device_count": 0,
                "mixed_precision": ["fp32"],
                "inference_supported": False,
                "evidence": "Accelerator was reported available but property probe failed: " + type(exc).__name__,
            }

    try:
        xpu_available = bool(
            hasattr(torch_module, "xpu") and torch_module.xpu.is_available()
        )
    except Exception:
        xpu_available = False
    if xpu_available:
        try:
            return {
                "pytorch_available": True,
                "training_runtime": "intel_xpu",
                "device_name": str(torch_module.xpu.get_device_name(0)),
                "device_count": int(torch_module.xpu.device_count()),
                "total_device_memory_bytes": None,
                "mixed_precision": ["fp32"],
                "inference_supported": False,
                "evidence": "PyTorch Intel XPU runtime detected locally; MKAOS Rust inference support remains unverified.",
            }
        except Exception as exc:
            return {
                "pytorch_available": True,
                "training_runtime": "intel_xpu_probe_failed",
                "device_name": None,
                "device_count": 0,
                "mixed_precision": ["fp32"],
                "inference_supported": False,
                "evidence": "Intel XPU probe failed: " + type(exc).__name__,
            }

    try:
        mps_available = bool(
            hasattr(torch_module, "backends")
            and hasattr(torch_module.backends, "mps")
            and torch_module.backends.mps.is_available()
        )
    except Exception:
        mps_available = False
    if mps_available:
        return {
            "pytorch_available": True,
            "training_runtime": "apple_metal",
            "device_name": "Apple Metal (MPS)",
            "device_count": 1,
            "total_device_memory_bytes": None,
            "mixed_precision": ["fp32"],
            "inference_supported": False,
            "evidence": "PyTorch MPS runtime detected locally; MKAOS Rust inference support remains unverified.",
        }

    return {
        "pytorch_available": True,
        "training_runtime": "cpu",
        "device_name": "CPU",
        "device_count": 1,
        "total_device_memory_bytes": None,
        "mixed_precision": ["fp32"],
        "inference_supported": False,
        "evidence": "PyTorch CPU training runtime available; no compatible accelerator was detected.",
    }


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
