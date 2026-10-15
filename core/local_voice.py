"""Local-only Turkish speech adapters.

No model downloads or cloud APIs happen here. Install voice/STT models yourself,
store them under the configured local model directory, and keep network egress blocked.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

VOICE_DIR = Path(os.getenv("SEKA_VOICE_MODEL_DIR", "./models/voices")).resolve()
PIPER_BIN = os.getenv("PIPER_EXECUTABLE", "piper")
WHISPER_BIN = os.getenv("WHISPER_CPP_BIN", "whisper-cli")
WHISPER_MODEL = os.getenv("WHISPER_MODEL_PATH", "").strip()
VOICE_MODELS = {
    "male": os.getenv("SEKA_VOICE_MALE_MODEL", "tr_TR-fettah-medium.onnx"),
    "female": os.getenv("SEKA_VOICE_FEMALE_MODEL", "tr_TR-dfki-medium.onnx"),
}


class LocalVoiceError(RuntimeError):
    pass


def _model_path(voice: str) -> Path:
    if voice not in VOICE_MODELS:
        raise LocalVoiceError("Ses seçimi geçersiz.")
    root = VOICE_DIR.resolve()
    path = (root / VOICE_MODELS[voice]).resolve()
    if root not in path.parents or not path.is_file():
        raise LocalVoiceError(
            f"Yerel {voice} sesi bulunamadı. Model dosyasını {root} dizinine yerleştir."
        )
    return path


def voice_status() -> dict:
    return {
        "mode": "local-only",
        "piper_available": shutil.which(PIPER_BIN) is not None,
        "whisper_available": shutil.which(WHISPER_BIN) is not None and bool(WHISPER_MODEL and Path(WHISPER_MODEL).is_file()),
        "voices": {
            key: {"configured": (VOICE_DIR / filename).is_file(), "file": filename}
            for key, filename in VOICE_MODELS.items()
        },
        "cat_effect_available": shutil.which("ffmpeg") is not None,
    }


def synthesize(text: str, voice: str = "male", cat_mode: bool = False) -> bytes:
    clean = " ".join(str(text).split())
    if not clean:
        raise LocalVoiceError("Seslendirilecek metin boş.")
    if len(clean) > 4000:
        raise LocalVoiceError("Tek seferde en fazla 4.000 karakter seslendirilebilir.")
    executable = shutil.which(PIPER_BIN)
    if not executable:
        raise LocalVoiceError("Yerel Piper kurulmamış. PIPER_EXECUTABLE ayarını kontrol et.")
    model = _model_path(voice)
    output_dir = Path("./memory/voice")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="seka-voice-", dir=str(output_dir)) as temp_dir:
        wav_path = Path(temp_dir) / "speech.wav"
        result = subprocess.run(
            [executable, "--model", str(model), "--output_file", str(wav_path)],
            input=clean.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
            check=False,
        )
        if result.returncode != 0 or not wav_path.is_file():
            raise LocalVoiceError("Yerel ses üretimi başarısız oldu; model ve Piper kurulumunu kontrol et.")
        if cat_mode:
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                raise LocalVoiceError("Kedi dublajı için yerel ffmpeg kurulmalı.")
            cat_path = Path(temp_dir) / "cat.wav"
            effect = subprocess.run(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav_path),
                 "-af", "asetrate=44100*1.32,aresample=44100,atempo=0.76",
                 str(cat_path)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
            )
            if effect.returncode != 0 or not cat_path.is_file():
                raise LocalVoiceError("Kedi dublajı efekti uygulanamadı.")
            wav_path = cat_path
        return wav_path.read_bytes()


def transcribe(audio: bytes, suffix: str = ".webm") -> str:
    executable = shutil.which(WHISPER_BIN)
    model = Path(WHISPER_MODEL).expanduser().resolve() if WHISPER_MODEL else None
    if not executable or not model or not model.is_file():
        raise LocalVoiceError(
            "Yerel Türkçe konuşma tanıma hazır değil. whisper.cpp ve yerel model yolunu yapılandır."
        )
    if not audio or len(audio) > 15 * 1024 * 1024:
        raise LocalVoiceError("Ses dosyası boş veya 15 MB sınırını aşıyor.")
    safe_suffix = suffix if suffix in {".webm", ".wav", ".mp3", ".m4a", ".ogg"} else ".webm"
    with tempfile.TemporaryDirectory(prefix="seka-stt-") as temp_dir:
        audio_path = Path(temp_dir) / ("input" + safe_suffix)
        audio_path.write_bytes(audio)
        result = subprocess.run(
            [executable, "-m", str(model), "-f", str(audio_path), "-l", "tr", "-nt", "-np"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False,
        )
        if result.returncode != 0:
            raise LocalVoiceError("Yerel konuşma tanıma başarısız oldu.")
        text = result.stdout.decode("utf-8", errors="replace").strip()
        if not text:
            raise LocalVoiceError("Konuşmadan metin çıkarılamadı.")
        return text[:8000]
