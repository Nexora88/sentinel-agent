"""Explicit native Rust MKAOS chat adapter.

Fails closed when no locally trained checkpoint is configured. Never downloads
weights or silently falls back to a third-party model. Prompts are framed in Turkish.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Mapping

from core.language_policy import wrap_user_prompt


class NativeMkaosUnavailable(RuntimeError):
    """Native model is not configured or generation failed safely."""


def generate_native_reply(prompt: str, env: Mapping[str, str] | None = None) -> str:
    settings = os.environ if env is None else env
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be non-empty")

    # Turkish-first chat frame before byte/token limits
    framed = wrap_user_prompt(prompt.strip())
    if len(framed.encode("utf-8")) > int(settings.get("MKAOS_NATIVE_MAX_PROMPT_BYTES", "16000")):
        raise ValueError("prompt exceeds the configured native-model limit")

    checkpoint_value = settings.get("MKAOS_NATIVE_CHECKPOINT", "").strip()
    expected_hash = settings.get("MKAOS_NATIVE_SHA256", "").strip().lower()
    if not checkpoint_value:
        raise NativeMkaosUnavailable(
            "Yerel MKAOS checkpoint yapılandırılmadı. Onaylı eğitim sonrası "
            "MKAOS_NATIVE_CHECKPOINT ve MKAOS_NATIVE_SHA256 ayarlayın."
        )
    if not expected_hash:
        raise NativeMkaosUnavailable(
            "MKAOS_NATIVE_SHA256 zorunlu; gözden geçirilmiş checkpoint'in SHA-256 özetini yazın."
        )
    checkpoint = Path(checkpoint_value).expanduser().resolve()
    if not checkpoint.is_file():
        raise NativeMkaosUnavailable("Yapılandırılan yerel MKAOS checkpoint dosyası bulunamadı.")
    if len(expected_hash) != 64 or any(c not in "0123456789abcdef" for c in expected_hash):
        raise NativeMkaosUnavailable("MKAOS_NATIVE_SHA256 64 karakterlik onaltılık SHA-256 olmalıdır.")

    generator = Path(settings.get("MKAOS_NATIVE_GENERATOR", "/usr/local/bin/mkaos-generate")).expanduser()
    if not generator.is_file():
        raise NativeMkaosUnavailable("Yerel Rust üretici ikilisi bu kurulumda yok.")

    def integer(name: str, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(settings.get(name, str(default)))
        except (TypeError, ValueError) as exc:
            raise NativeMkaosUnavailable(f"{name} tamsayı olmalı.") from exc
        if not minimum <= value <= maximum:
            raise NativeMkaosUnavailable(f"{name} {minimum}–{maximum} aralığında olmalı.")
        return value

    heads = integer("MKAOS_NATIVE_HEADS", 4, 1, 128)
    kv_heads = integer("MKAOS_NATIVE_KV_HEADS", 2, 1, 128)
    max_seq = integer("MKAOS_NATIVE_MAX_SEQ", 2048, 2, 32768)
    max_new = integer("MKAOS_NATIVE_MAX_NEW_TOKENS", 256, 1, 2048)
    timeout = integer("MKAOS_NATIVE_TIMEOUT_SECONDS", 90, 1, 600)
    if heads % kv_heads:
        raise NativeMkaosUnavailable("MKAOS_NATIVE_HEADS, KV_HEADS'e tam bölünmeli.")
    prompt_tokens = len(framed.encode("utf-8"))
    if prompt_tokens + max_new > max_seq:
        raise ValueError("İstem + üretim MKAOS_NATIVE_MAX_SEQ sınırını aşıyor.")

    command = [
        str(generator),
        "--checkpoint",
        str(checkpoint),
        "--sha256",
        expected_hash,
        "--heads",
        str(heads),
        "--kv-heads",
        str(kv_heads),
        "--max-seq",
        str(max_seq),
        "--max-new-tokens",
        str(max_new),
        "--prompt",
        framed,
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            close_fds=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise NativeMkaosUnavailable("Yerel MKAOS üretimi zaman aşımına uğradı.") from exc
    except OSError as exc:
        raise NativeMkaosUnavailable("Yerel MKAOS üreticisi başlatılamadı.") from exc
    if completed.returncode != 0:
        raise NativeMkaosUnavailable(
            f"Yerel MKAOS üretimi güvenli şekilde başarısız (kod {completed.returncode}). "
            "Checkpoint bütünlüğünü ve model boyutlarını kontrol edin."
        )
    reply = completed.stdout.strip()
    if not reply:
        raise NativeMkaosUnavailable("Yerel MKAOS boş yanıt üretti.")
    if len(reply.encode("utf-8")) > 256_000:
        raise NativeMkaosUnavailable("Yerel MKAOS yanıtı güvenlik sınırını aştı.")
    return reply
