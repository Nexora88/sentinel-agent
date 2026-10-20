"""Local-only Turkish speech adapters.

No model downloads or cloud APIs happen here. Install voice/STT models yourself,
store them under the configured local model directory, and keep network egress blocked.
"""
from __future__ import annotations

import os
import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path

VOICE_DIR = Path(os.getenv("SEKA_VOICE_MODEL_DIR", "./models/voices")).resolve()
PIPER_BIN = os.getenv("PIPER_EXECUTABLE", "piper")
WHISPER_BIN = os.getenv("WHISPER_CPP_BIN", "whisper-cli")
WHISPER_MODEL = os.getenv("WHISPER_MODEL_PATH", "").strip()
FASTER_WHISPER_MODEL = os.getenv("FASTER_WHISPER_MODEL_PATH", "./models/whisper-small").strip()
VOICE_MODELS = {
    "male": os.getenv("SEKA_VOICE_MALE_MODEL", "tr_TR-fettah-medium.onnx"),
    "female": os.getenv("SEKA_VOICE_FEMALE_MODEL", "tr_TR-dfki-medium.onnx"),
}
# Product display names and style targets; the installed voice model determines the actual timbre.
VOICE_PROFILES = {
    "male": {"name": "Bora", "style": "tok, sakin, bilge ve güven veren", "default_pace": 0.96},
    "female": {"name": "Defne", "style": "sıcak, net, akıcı ve enerjik", "default_pace": 1.04},
}


class LocalVoiceError(RuntimeError):
    pass


def _model_path(voice: str) -> Path:
    if voice not in VOICE_MODELS:
        raise LocalVoiceError("Ses seçimi geçersiz.")
    root = VOICE_DIR.resolve()
    path = (root / VOICE_MODELS[voice]).resolve()
    sidecar = path.with_suffix(path.suffix + ".json")
    if root not in path.parents or not path.is_file() or not sidecar.is_file():
        raise LocalVoiceError(
            f"Yerel {voice} sesi veya .onnx.json eş dosyası bulunamadı. Modeli {root} dizinine yerleştir."
        )
    return path


def voice_status() -> dict:
    return {
        "mode": "local-only",
        "piper_available": shutil.which(PIPER_BIN) is not None,
        "whisper_cpp_available": shutil.which(WHISPER_BIN) is not None and bool(WHISPER_MODEL and Path(WHISPER_MODEL).is_file()),
        "faster_whisper_available": importlib.util.find_spec("faster_whisper") is not None and Path(FASTER_WHISPER_MODEL).is_dir(),
        "whisper_available": (shutil.which(WHISPER_BIN) is not None and bool(WHISPER_MODEL and Path(WHISPER_MODEL).is_file())) or (__import__("importlib.util").util.find_spec("faster_whisper") is not None and Path(FASTER_WHISPER_MODEL).is_dir()),
        "voices": {
            key: {
                "name": VOICE_PROFILES[key]["name"],
                "style_target": VOICE_PROFILES[key]["style"],
                "default_pace": VOICE_PROFILES[key]["default_pace"],
                "configured": (VOICE_DIR / filename).is_file()
                    and (VOICE_DIR / filename).with_suffix(Path(filename).suffix + ".json").is_file(),
                "file": filename,
            }
            for key, filename in VOICE_MODELS.items()
        },
        "cat_effect_available": shutil.which("ffmpeg") is not None,
    }


def speech_length_scale(voice: str, pace: float = 1.0) -> float:
    """Return a bounded Piper length scale for a voice character and speaking pace."""
    if voice not in VOICE_MODELS:
        raise LocalVoiceError("Ses seçimi geçersiz.")
    try:
        pace_value = float(pace)
    except (TypeError, ValueError) as exc:
        raise LocalVoiceError("Konuşma hızı 0,85 ile 1,15 arasında olmalı.") from exc
    if not 0.85 <= pace_value <= 1.15:
        raise LocalVoiceError("Konuşma hızı 0,85 ile 1,15 arasında olmalı.")
    # Male profile is deliberately slower/deeper; female profile is brisker.
    base_scale = 1.08 if voice == "male" else 0.92
    return round(base_scale / pace_value, 3)


def synthesize(text: str, voice: str = "male", cat_mode: bool = False, pace: float | None = None) -> bytes:
    clean = " ".join(str(text).split())
    if not clean:
        raise LocalVoiceError("Seslendirilecek metin boş.")
    if len(clean) > 4000:
        raise LocalVoiceError("Tek seferde en fazla 4.000 karakter seslendirilebilir.")
    if voice not in VOICE_PROFILES:
        raise LocalVoiceError("Ses seçimi geçersiz.")
    if pace is None:
        pace = VOICE_PROFILES[voice]["default_pace"]
    executable = shutil.which(PIPER_BIN)
    if not executable:
        raise LocalVoiceError("Yerel Piper kurulmamış. PIPER_EXECUTABLE ayarını kontrol et.")
    model = _model_path(voice)
    length_scale = speech_length_scale(voice, pace)
    output_dir = Path("./memory/voice")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="seka-voice-", dir=str(output_dir)) as temp_dir:
        wav_path = Path(temp_dir) / "speech.wav"
        result = subprocess.run(
            [
                executable, "--model", str(model),
                "--length_scale", str(length_scale),
                "--noise_scale", "0.667",
                "--noise_w", "0.8",
                "--sentence_silence", "0.18",
                "--output_file", str(wav_path),
            ],
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
    if not audio or len(audio) > 15 * 1024 * 1024:
        raise LocalVoiceError("Ses dosyası boş veya 15 MB sınırını aşıyor.")
    safe_suffix = suffix if suffix in {".webm", ".wav", ".mp3", ".m4a", ".ogg"} else ".webm"
    with tempfile.TemporaryDirectory(prefix="seka-stt-") as temp_dir:
        audio_path = Path(temp_dir) / ("input" + safe_suffix)
        audio_path.write_bytes(audio)
        faster_model = Path(FASTER_WHISPER_MODEL).expanduser().resolve()
        if faster_model.is_dir():
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                pass
            else:
                try:
                    # local_files_only prevents downloading a model at runtime.
                    model = WhisperModel(
                        str(faster_model), device="cpu", compute_type="int8",
                        local_files_only=True,
                    )
                    segments, _info = model.transcribe(
                        str(audio_path), language="tr", vad_filter=True,
                        beam_size=3, condition_on_previous_text=False,
                    )
                    text = " ".join(segment.text.strip() for segment in segments).strip()
                    if text:
                        return text[:8000]
                except Exception as exc:
                    raise LocalVoiceError("Yerel faster-whisper modeli çözümlenemedi; model dosyalarını denetle.") from exc
        executable = shutil.which(WHISPER_BIN)
        model = Path(WHISPER_MODEL).expanduser().resolve() if WHISPER_MODEL else None
        if not executable or not model or not model.is_file():
            raise LocalVoiceError(
                "Yerel Türkçe konuşma tanıma hazır değil. faster-whisper model klasörünü veya whisper.cpp model yolunu yapılandır."
            )
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
