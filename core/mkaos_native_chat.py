"""Explicit native Rust MKAOS chat adapter.

The adapter fails closed when no locally trained checkpoint is configured. It never
downloads weights or silently falls back to a third-party model.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Mapping


class NativeMkaosUnavailable(RuntimeError):
    """Native model is not configured or generation failed safely."""


def generate_native_reply(prompt: str, env: Mapping[str, str] | None = None) -> str:
    settings = os.environ if env is None else env
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be non-empty")
    if len(prompt.encode("utf-8")) > int(settings.get("MKAOS_NATIVE_MAX_PROMPT_BYTES", "16000")):
        raise ValueError("prompt exceeds the configured native-model limit")

    checkpoint_value = settings.get("MKAOS_NATIVE_CHECKPOINT", "").strip()
    expected_hash = settings.get("MKAOS_NATIVE_SHA256", "").strip().lower()
    if not checkpoint_value:
        raise NativeMkaosUnavailable(
            "Native MKAOS checkpoint is not configured. Set MKAOS_NATIVE_CHECKPOINT to a reviewed local checkpoint."
        )
    if not expected_hash:
        raise NativeMkaosUnavailable(
            "MKAOS_NATIVE_SHA256 is required; set the reviewed checkpoint's SHA-256 digest."
        )
    checkpoint = Path(checkpoint_value).expanduser().resolve()
    if not checkpoint.is_file():
        raise NativeMkaosUnavailable("Configured native MKAOS checkpoint file is not available locally.")
    if len(expected_hash) != 64 or any(c not in "0123456789abcdef" for c in expected_hash):
        raise NativeMkaosUnavailable("MKAOS_NATIVE_SHA256 must be a 64-character hexadecimal SHA-256.")

    # Verify integrity before spawning the native runtime; Rust independently checks it too.
    digest = hashlib.sha256()
    try:
        with checkpoint.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise NativeMkaosUnavailable("Configured native MKAOS checkpoint could not be read.") from exc
    if digest.hexdigest() != expected_hash:
        raise NativeMkaosUnavailable("Configured native MKAOS checkpoint SHA-256 does not match.")

    generator = Path(settings.get("MKAOS_NATIVE_GENERATOR", "/usr/local/bin/mkaos-generate")).expanduser()
    if not generator.is_file():
        raise NativeMkaosUnavailable("Native Rust generator binary is missing from this installation.")

    def integer(name: str, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(settings.get(name, str(default)))
        except (TypeError, ValueError) as exc:
            raise NativeMkaosUnavailable(f"{name} must be an integer.") from exc
        if not minimum <= value <= maximum:
            raise NativeMkaosUnavailable(f"{name} must be between {minimum} and {maximum}.")
        return value

    heads = integer("MKAOS_NATIVE_HEADS", 4, 1, 128)
    kv_heads = integer("MKAOS_NATIVE_KV_HEADS", 2, 1, 128)
    max_seq = integer("MKAOS_NATIVE_MAX_SEQ", 2048, 2, 32768)
    max_new = integer("MKAOS_NATIVE_MAX_NEW_TOKENS", 256, 1, 2048)
    timeout = integer("MKAOS_NATIVE_TIMEOUT_SECONDS", 90, 1, 600)
    if heads % kv_heads:
        raise NativeMkaosUnavailable("MKAOS_NATIVE_HEADS must be divisible by MKAOS_NATIVE_KV_HEADS.")
    prompt_tokens = len(prompt.encode("utf-8"))
    if prompt_tokens + max_new > max_seq:
        raise ValueError("Prompt plus requested generation exceeds MKAOS_NATIVE_MAX_SEQ.")

    command = [
        str(generator), "--checkpoint", str(checkpoint), "--sha256", expected_hash,
        "--heads", str(heads), "--kv-heads", str(kv_heads), "--max-seq", str(max_seq),
        "--max-new-tokens", str(max_new), "--prompt", prompt,
    ]
    try:
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, shell=False, close_fds=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise NativeMkaosUnavailable("Native MKAOS generation exceeded its configured timeout.") from exc
    except OSError as exc:
        raise NativeMkaosUnavailable("Native MKAOS generator could not be started.") from exc
    if completed.returncode != 0:
        # Keep internal stderr/paths out of HTTP errors and logs.
        raise NativeMkaosUnavailable(
            f"Native MKAOS generation failed safely (exit code {completed.returncode}). "
            "Check local checkpoint integrity and model dimensions."
        )
    reply = completed.stdout.strip()
    if not reply:
        raise NativeMkaosUnavailable("Native MKAOS produced an empty response.")
    if len(reply.encode("utf-8")) > 256_000:
        raise NativeMkaosUnavailable("Native MKAOS response exceeded the configured output safety limit.")
    return reply
