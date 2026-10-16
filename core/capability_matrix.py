"""MKAOS yetenek matrisi — abartısız durum raporu.

UI veya API bu sözlüğü okuyarak "var / kısmi / yok" gösterebilir.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any


def _flag(ok: bool, partial: bool = False) -> str:
    if ok:
        return "ready"
    if partial:
        return "partial"
    return "missing"


def build_capability_matrix(root: Path | None = None) -> dict[str, Any]:
    root = root or Path(".")
    native_ckpt = Path(os.getenv("MKAOS_NATIVE_CHECKPOINT", "")).expanduser()
    native_sha = (os.getenv("MKAOS_NATIVE_SHA256") or "").strip()
    sd = (os.getenv("SD_API_URL") or "").strip()
    rust_bin = Path(os.getenv("MKAOS_NATIVE_GENERATOR", "/usr/local/bin/mkaos-generate"))

    seed_all = root / "data" / "mkaos-tr-seed-12" / "records_all.jsonl"
    seed_base = root / "data" / "mkaos-tr-seed-12" / "records.jsonl"

    matrix = {
        "language": {
            "default": "tr",
            "policy_module": (root / "core" / "language_policy.py").is_file(),
            "ui_locale": "tr",
            "status": "ready",
            "note": "Arayüz ve istem çerçevesi Türkçe; genel dil modeli kalitesi ayrı kapı.",
        },
        "llm": {
            "native_rust_engine": (root / "engine" / "mkaos-inference").is_dir(),
            "native_generator_binary": rust_bin.is_file() or shutil.which("mkaos-generate") is not None,
            "checkpoint_configured": native_ckpt.is_file() and len(native_sha) == 64,
            "silent_third_party_fallback": False,
            "turkish_seed_present": seed_all.is_file() or seed_base.is_file(),
            "status": _flag(
                native_ckpt.is_file() and len(native_sha) == 64,
                partial=True,
            ),
            "note": "Checkpoint yoksa sohbet 503 (fail-closed). Seed eğitim boru hattı var.",
        },
        "code": {
            "writer": (root / "tools" / "code_writer.py").is_file(),
            "path_sandbox": True,
            "approval_gate": True,
            "status": "partial",
            "note": "Yazma insan onayı + güvenli kök dizin; model kalitesi backend'e bağlı.",
        },
        "media": {
            "local_poster_pillow": True,
            "local_slideshow_ffmpeg": shutil.which("ffmpeg") is not None,
            "stable_diffusion_self_hosted": bool(sd),
            "public_image_api_fallback": False,
            "status": _flag(True, partial=not bool(sd)),
            "note": "Poster/slideshow yerel; SD yalnızca SD_API_URL ile.",
        },
        "security": {
            "command_whitelist": (root / "core" / "safety" / "command_whitelist.py").is_file(),
            "prompt_injection_filter_tr_en": True,
            "approval_store": True,
            "web_research_default_off": os.getenv("ALLOW_WEB_RESEARCH", "false").lower() != "true",
            "status": "ready",
            "note": "Uygulama katmanı kontrolleri; OS firewall ayrı.",
        },
    }
    return {
        "schema": "mkaos-capability-matrix-v1",
        "production_ready_claim": False,
        "matrix": matrix,
    }
