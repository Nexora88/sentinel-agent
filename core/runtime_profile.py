"""Portable, conservative hardware profile for local MKAOS model guidance."""
from __future__ import annotations
import os
import platform
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


def _model_tier(total_ram_mb: int | None) -> dict[str, Any]:
    """Return cautious suggestions, never a fit/performance guarantee."""
    if total_ram_mb is None:
        return {"tier": "unknown", "suggested_chat_model": None,
                "suggested_code_model": None,
                "reason_tr": "RAM algılanamadı; model seçimini kullanıcı yapmalı."}
    if total_ram_mb < 3072:
        return {"tier": "minimal", "suggested_chat_model": None,
                "suggested_code_model": None,
                "reason_tr": "3 GB altı RAM: LLM garantisi yok; kuralsal temel işlevleri kullan."}
    if total_ram_mb < 6144:
        return {"tier": "low", "suggested_chat_model": "qwen2.5:0.5b",
                "suggested_code_model": None,
                "reason_tr": "Düşük RAM: küçük nicemlenmiş model dene ve gerçek bellek kullanımını ölç."}
    if total_ram_mb < 12288:
        return {"tier": "entry", "suggested_chat_model": "qwen2.5:1.5b",
                "suggested_code_model": "qwen2.5-coder:1.5b",
                "reason_tr": "Giriş seviyesi RAM: küçük modeller için başlangıç önerisi; kullanılabilir RAM değişebilir."}
    if total_ram_mb < 24576:
        return {"tier": "standard", "suggested_chat_model": "qwen2.5:3b",
                "suggested_code_model": "qwen2.5-coder:3b",
                "reason_tr": "Orta seviye RAM: 3B sınıfı model denemesi; cihaz testi gerekir."}
    return {"tier": "high", "suggested_chat_model": "qwen2.5:7b",
            "suggested_code_model": "qwen2.5-coder:7b",
            "reason_tr": "Yüksek RAM: 7B sınıfı denenebilir; VRAM ve nicemleme sonucu değiştirir."}


def get_runtime_profile(*, total_ram_mb: int | None = None,
                        system: str | None = None, machine: str | None = None,
                        cpu_count: int | None = None) -> dict[str, Any]:
    """Describe this host and suggest local models without network access.

    Optional values make the policy deterministic and testable.
    """
    detected_ram = _detect_total_ram_mb() if total_ram_mb is None else max(0, int(total_ram_mb))
    model = _model_tier(detected_ram)
    return {
        "platform": system or platform.system() or "Unknown",
        "architecture": machine or platform.machine() or "Unknown",
        "cpu_count": max(1, int(cpu_count if cpu_count is not None else (os.cpu_count() or 1))),
        "total_ram_mb": detected_ram,
        "gpu_backend": "unknown",
        "gpu_note_tr": "GPU/VRAM henüz algılanmıyor; CUDA, ROCm, Metal ve CPU adaptörleri ayrıca doğrulanmalı.",
        "network_requests_made": False,
        "model_guidance": model,
        "limitations_tr": [
            "Bu profil uyumluluk garantisi değil, başlangıç önerisidir.",
            "Toplam RAM, kullanılabilir RAM ile aynı değildir.",
            "Model dosyaları önceden kurulmuş olmalıdır; bu modül internet kullanmaz.",
            "Android'de cihaz üzerinde LLM için ayrıca desteklenen yerel çalışma zamanı ve yeterli kaynak gerekir.",
        ],
    }
