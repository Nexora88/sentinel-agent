"""Portable, conservative hardware profile for local MKAOS model guidance."""
from __future__ import annotations
import os
import platform
import subprocess
from typing import Any


def _detect_total_ram_mb() -> int | None:
    """Best-effort RAM detection using only the standard library."""
    try:
        with open("/proc/meminfo", "r", encoding="ascii") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    return max(1, int(line.split()[1]) // 1024)
    except (OSError, ValueError, IndexError):
        pass

    if platform.system() == "Windows":
        try:
            import ctypes
            from ctypes import wintypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return max(1, int(status.ullTotalPhys // (1024 * 1024)))
        except (AttributeError, OSError, TypeError, ValueError):
            pass

    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        if pages > 0 and page_size > 0:
            return max(1, int(pages * page_size // (1024 * 1024)))
    except (AttributeError, OSError, ValueError):
        pass
    return None


def _detect_total_vram_mb() -> int | None:
    """Detect NVIDIA VRAM if nvidia-smi exists; no network access or installation."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=1.5, check=False,
        )
        if result.returncode != 0:
            return None
        values = [int(line.strip()) for line in result.stdout.splitlines() if line.strip().isdigit()]
        return max(values) if values else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _model_tier(total_ram_mb: int | None, total_vram_mb: int | None = None) -> dict[str, Any]:
    """Return cautious suggestions, never a fit/performance guarantee."""
    if total_ram_mb is None:
        return {"tier": "unknown", "suggested_chat_model": None,
                "suggested_code_model": None, "suggested_context_tokens": 0,
                "reason_tr": "RAM algılanamadı; model seçimini kullanıcı yapmalı."}
    if total_ram_mb < 3072:
        return {"tier": "minimal", "suggested_chat_model": None,
                "suggested_code_model": None, "suggested_context_tokens": 0,
                "reason_tr": "3 GB altı RAM: LLM garantisi yok; kuralsal temel işlevleri kullan."}
    if total_ram_mb < 6144:
        return {"tier": "low", "suggested_chat_model": "qwen2.5:0.5b",
                "suggested_code_model": None, "suggested_context_tokens": 2048,
                "reason_tr": "Düşük RAM: küçük nicemlenmiş model dene ve gerçek bellek kullanımını ölç."}
    if total_ram_mb < 12288:
        return {"tier": "entry", "suggested_chat_model": "qwen2.5:1.5b",
                "suggested_code_model": "qwen2.5-coder:1.5b", "suggested_context_tokens": 4096,
                "reason_tr": "Giriş seviyesi RAM: küçük modeller için başlangıç önerisi; kullanılabilir RAM değişebilir."}
    if total_ram_mb < 24576:
        return {"tier": "standard", "suggested_chat_model": "qwen2.5:3b",
                "suggested_code_model": "qwen2.5-coder:3b", "suggested_context_tokens": 8192,
                "reason_tr": "Orta seviye RAM: 3B sınıfı model denemesi; cihaz testi gerekir."}
    return {"tier": "high", "suggested_chat_model": "qwen2.5:7b",
            "suggested_code_model": "qwen2.5-coder:7b", "suggested_context_tokens": 8192,
            "reason_tr": "Yüksek RAM: 7B sınıfı denenebilir; VRAM ve nicemleme sonucu değiştirir."}


def get_runtime_profile(*, total_ram_mb: int | None = None,
                        total_vram_mb: int | None = None,
                        system: str | None = None, machine: str | None = None,
                        cpu_count: int | None = None) -> dict[str, Any]:
    """Describe this host and suggest local models without network access.

    Optional values make the policy deterministic and testable.
    """
    detected_ram = _detect_total_ram_mb() if total_ram_mb is None else max(0, int(total_ram_mb))
    detected_vram = _detect_total_vram_mb() if total_vram_mb is None else max(0, int(total_vram_mb))
    model = _model_tier(detected_ram, detected_vram)
    if model.get("suggested_context_tokens", 0) and detected_vram is not None:
        cap = 2048 if detected_vram < 4096 else 4096 if detected_vram < 8192 else 8192
        model["suggested_context_tokens"] = min(model["suggested_context_tokens"], cap)
        model["reason_tr"] += " Bağlam uzunluğu algılanan VRAM'e göre sınırlandı; gerçek model testi gerekir."
    return {
        "platform": system or platform.system() or "Unknown",
        "architecture": machine or platform.machine() or "Unknown",
        "cpu_count": max(1, int(cpu_count if cpu_count is not None else (os.cpu_count() or 1))),
        "total_ram_mb": detected_ram,
        "total_vram_mb": detected_vram,
        "gpu_backend": "nvidia_detected_unverified" if detected_vram is not None else "unknown",
        "gpu_note_tr": "NVIDIA VRAM algılandıysa bu yalnızca donanım keşfidir; çıkarım desteği ayrıca test edilmelidir.",
        "network_requests_made": False,
        "model_guidance": model,
        "limitations_tr": [
            "Bu profil uyumluluk garantisi değil, başlangıç önerisidir.",
            "Toplam RAM, kullanılabilir RAM ile aynı değildir.",
            "Model dosyaları önceden kurulmuş olmalıdır; bu modül internet kullanmaz.",
            "Android'de cihaz üzerinde LLM için ayrıca desteklenen yerel çalışma zamanı ve yeterli kaynak gerekir.",
        ],
    }
