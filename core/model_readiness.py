"""Safe readiness diagnostics for the native MKAOS model.

This module never downloads model assets and never returns local filesystem paths.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path


def native_model_readiness(env=None) -> dict[str, str | bool]:
    settings = os.environ if env is None else env
    checkpoint_value = settings.get("MKAOS_NATIVE_CHECKPOINT", "/app/models/mkaos/model.mkaosw").strip()
    expected_hash = settings.get("MKAOS_NATIVE_SHA256", "").strip().lower()
    generator_value = settings.get("MKAOS_NATIVE_GENERATOR", "/usr/local/bin/mkaos-generate").strip()

    if not checkpoint_value:
        return {"ready": False, "status": "checkpoint_not_configured", "message": "Yerel MKAOS modeli yapılandırılmamış."}
    if not expected_hash:
        return {"ready": False, "status": "checkpoint_hash_not_pinned", "message": "Model SHA-256 doğrulaması yapılandırılmamış."}
    if len(expected_hash) != 64 or any(ch not in "0123456789abcdef" for ch in expected_hash):
        return {"ready": False, "status": "invalid_checkpoint_hash", "message": "Model SHA-256 değeri geçersiz."}

    checkpoint = Path(checkpoint_value).expanduser()
    if not checkpoint.is_file():
        return {"ready": False, "status": "checkpoint_missing", "message": "Onaylı yerel model dosyası bulunamadı."}

    generator = Path(generator_value).expanduser()
    if not generator.is_file():
        return {"ready": False, "status": "generator_missing", "message": "Yerel Rust çıkarım ikilisi bulunamadı."}

    digest = hashlib.sha256()
    try:
        with checkpoint.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return {"ready": False, "status": "checkpoint_unreadable", "message": "Yerel model dosyası okunamıyor."}
    if digest.hexdigest() != expected_hash:
        return {"ready": False, "status": "checkpoint_hash_mismatch", "message": "Model dosyasının SHA-256 değeri yapılandırmayla eşleşmiyor."}

    return {"ready": True, "status": "checkpoint_hash_verified", "message": "Yerel model dosyası ve SHA-256 doğrulaması hazır."}
