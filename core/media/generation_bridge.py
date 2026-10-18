"""Model-independent media bridge. Adapters must be explicitly local/self-hosted."""
from __future__ import annotations
from typing import Any, Protocol

class MediaAdapter(Protocol):
    name: str
    def capabilities(self) -> dict: ...
    def execute(self, operation: str, payload: dict) -> dict: ...

class GenerationBridge:
    def __init__(self, adapters: list[MediaAdapter] | None = None):
        self.adapters = list(adapters or [])
        # Always offer offline canvas if nothing else configured
        if not any(getattr(a, "name", "") == "local-canvas" for a in self.adapters):
            self.adapters.append(LocalCanvasAdapter())
        if not any(getattr(a, "name", "") == LocalVideoFrameAnalysisAdapter.name for a in self.adapters):
            self.adapters.append(LocalVideoFrameAnalysisAdapter())
        if not any(getattr(a, "name", "") == TextToVideoAdapter.name for a in self.adapters):
            self.adapters.append(TextToVideoAdapter())

    def capabilities(self) -> dict:
        return {
            "adapter_count": len(self.adapters),
            "adapters": [a.capabilities() for a in self.adapters],
            "policy": "explicit adapters only; no public API fallback",
        }

    def execute(self, operation: str, payload: dict) -> dict:
        for adapter in self.adapters:
            caps = adapter.capabilities()
            if caps.get("enabled") and operation in caps.get("operations", []):
                return adapter.execute(operation, payload)
        raise RuntimeError(
            "Bu işlem için etkin, açıkça yapılandırılmış yerel model adaptörü yok; dış servise gönderilmedi."
        )


class LocalVisionAdapter:
    """Image understanding through an explicitly configured local Ollama vision model.

    This adapter never downloads models and never sends image bytes to a public service.
    It is enabled only for loopback/private hosts and a non-empty model name.
    """
    name = "local-ollama-vision"

    def __init__(self, base_url: str | None = None, model: str | None = None):
        import os
        from urllib.parse import urlparse
        self.base_url = (base_url if base_url is not None else os.getenv("MKAOS_OLLAMA_URL", "http://127.0.0.1:11434")).strip().rstrip("/")
        self.model = (model if model is not None else os.getenv("MKAOS_VISION_MODEL", "")).strip()
        parsed = urlparse(self.base_url)
        host = (parsed.hostname or "").lower()
        local_host = host in {"localhost", "127.0.0.1", "::1", "host.docker.internal"} or host.endswith(".internal")
        if parsed.scheme != "http" or not local_host or parsed.username or parsed.password:
            self.base_url = ""
        self.enabled = bool(self.base_url and self.model)

    def capabilities(self) -> dict:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "backend_configured": self.enabled,
            "operations": ["understand_image"] if self.enabled else [],
            "mode": "local_vision_model" if self.enabled else "unavailable",
            "model": self.model or None,
            "policy": "loopback/private local endpoint only; no model download or public fallback",
        }

    def execute(self, operation: str, payload: dict) -> dict:
        if operation != "understand_image" or not self.enabled:
            raise RuntimeError("Yerel g?rsel anlama modeli yap?land?r?lmam??.")
        import base64
        import io
        from pathlib import Path
        import requests
        raw = payload.get("image_bytes")
        if raw is None:
            path_value = payload.get("image_path")
            if not path_value:
                raise RuntimeError("G?rsel baytlar? veya yerel dosya yolu gerekli.")
            path = Path(str(path_value)).resolve()
            allowed_roots = [Path("./memory/uploads").resolve(), Path("./memory/generated_images").resolve()]
            if not path.is_file() or not any(root == path or root in path.parents for root in allowed_roots):
                raise RuntimeError("G?rsel yaln?zca izin verilen yerel medya dizinlerinden okunabilir.")
            if path.stat().st_size > 12 * 1024 * 1024:
                raise RuntimeError("G?rsel 12 MB s?n?r?n? a??yor.")
            raw = path.read_bytes()
        if not isinstance(raw, (bytes, bytearray)) or not raw or len(raw) > 12 * 1024 * 1024:
            raise RuntimeError("G?rsel bo? veya 12 MB s?n?r?n? a??yor.")
        try:
            from PIL import Image
            with Image.open(io.BytesIO(raw)) as image:
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                if image.width * image.height > 20_000_000:
                    raise RuntimeError("G?rsel 20 megapiksel s?n?r?n? a??yor.")
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("Desteklenmeyen veya bozuk g?rsel dosyas?.") from exc
        prompt = str(payload.get("prompt") or "G?rseli T?rk?e olarak a??kla; g?rd???n ile ??kar?m?n? ay?r.")[:2000]
        request_body = {"model": self.model, "stream": False, "messages": [{
            "role": "user", "content": prompt,
            "images": [base64.b64encode(bytes(raw)).decode("ascii")],
        }]}
        try:
            with requests.Session() as session:
                session.trust_env = False
                response = session.post(self.base_url + "/api/chat", json=request_body,
                                        timeout=(3, 120), allow_redirects=False)
            response.raise_for_status()
            data = response.json()
            answer = data.get("message", {}).get("content", "")
            if not isinstance(answer, str) or not answer.strip():
                raise RuntimeError("Yerel g?rsel modeli bo? yan?t verdi.")
            return {"success": True, "text": answer[:12000], "model": self.model,
                    "source": "local_ollama_vision", "network": False}
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("Yerel g?rsel modeline ula??lamad? veya yan?t? okunamad?; d?? servise ge?i? yap?lmad?.") from exc


class LocalCanvasAdapter:
    """Pillow + ffmpeg — ağ ve SD zorunlu değil."""
    name = "local-canvas"

    def capabilities(self) -> dict:
        return {
            "name": self.name,
            "enabled": True,
            "backend_configured": True,
            "operations": ["poster", "code_card", "slideshow", "report_infographic"],
            "policy": "offline local only",
        }

    def execute(self, operation: str, payload: dict) -> dict:
        from core.media.local_canvas import LocalCanvas

        canvas = LocalCanvas(payload.get("output_dir", "./memory/generated_images"))
        if operation == "poster":
            return canvas.poster(payload.get("title", "MKAOS"), payload.get("body", ""))
        if operation == "code_card":
            return canvas.code_card(
                payload.get("language", "python"),
                payload.get("snippet", ""),
                title=payload.get("title", "Kod"),
            )
        if operation == "slideshow":
            return canvas.slideshow(
                payload.get("images") or payload.get("image_paths") or [],
                duration_per_frame=float(payload.get("duration_per_frame", 2.0)),
            )
        if operation == "report_infographic":
            return canvas.poster("Rapor", payload.get("report_text") or payload.get("body", ""))
        raise RuntimeError("local-canvas bu işlemi desteklemiyor.")


class LocalVideoFrameAnalysisAdapter:
    """Analyze bounded, deterministically sampled frames with the local vision adapter."""
    name = "local-video-frame-analysis"

    def __init__(self, vision: LocalVisionAdapter | None = None, *, ffmpeg: str | None = None,
                 ffprobe: str | None = None):
        import shutil
        self.vision = vision or LocalVisionAdapter()
        self.ffmpeg = ffmpeg or shutil.which("ffmpeg")
        self.ffprobe = ffprobe or shutil.which("ffprobe")

    def capabilities(self) -> dict:
        enabled = bool(self.ffmpeg and self.ffprobe and self.vision.capabilities().get("enabled"))
        return {"name": self.name, "enabled": enabled,
                "operations": ["analyze_video_frames"] if enabled else [],
                "mode": "sampled_frames_only" if enabled else "unavailable",
                "policy": "local video file, ffmpeg, and explicitly configured local vision model; no public fallback"}

    def execute(self, operation: str, payload: dict) -> dict:
        import subprocess
        from pathlib import Path
        if operation != "analyze_video_frames" or not self.capabilities()["enabled"]:
            raise RuntimeError("Yerel video-kare analiz adaptörü hazır değil.")
        video = Path(str(payload.get("video_path", ""))).resolve()
        allowed_roots = [Path("./memory/uploads").resolve(), Path("./memory/videos").resolve()]
        if not video.is_file() or not any(root == video or root in video.parents for root in allowed_roots):
            raise RuntimeError("Video yalnızca izin verilen yerel medya dizinlerinden okunabilir.")
        if video.stat().st_size > 100 * 1024 * 1024:
            raise RuntimeError("Video 100 MB sınırını aşıyor.")
        try:
            probe = subprocess.run([self.ffprobe, "-v", "error", "-show_entries", "format=duration",
                                    "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
                                   capture_output=True, text=True, timeout=10, check=True)
            duration = float(probe.stdout.strip())
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            raise RuntimeError("Video süresi okunamadı.") from exc
        if not 0 < duration <= 300:
            raise RuntimeError("Video süresi 0 ile 300 saniye arasında olmalıdır.")
        try:
            count = int(payload.get("frame_count", 6))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("frame_count 1 ile 12 arasında tam sayı olmalıdır.") from exc
        if not 1 <= count <= 12:
            raise RuntimeError("frame_count 1 ile 12 arasında olmalıdır.")
        timestamps = [duration * (i + 0.5) / count for i in range(count)]
        frames = []
        for timestamp in timestamps:
            try:
                result = subprocess.run([self.ffmpeg, "-v", "error", "-ss", f"{timestamp:.3f}",
                                         "-i", str(video), "-frames:v", "1", "-f", "image2pipe",
                                         "-vcodec", "png", "pipe:1"], capture_output=True, timeout=20, check=True)
            except (OSError, subprocess.SubprocessError) as exc:
                raise RuntimeError("Yerel video karesi çıkarılamadı.") from exc
            if not result.stdout or len(result.stdout) > 12 * 1024 * 1024:
                raise RuntimeError("Video karesi boş veya 12 MB sınırını aşıyor.")
            answer = self.vision.execute("understand_image", {
                "image_bytes": result.stdout,
                "prompt": f"Bu video karesini Türkçe açıkla. Zaman damgası {timestamp:.2f} saniye. "
                          "Yalnızca karede görülenleri belirt; video boyunca hareket hakkında çıkarım yapma. "
                          + str(payload.get("prompt", "") or "")[:1000],
            })
            frames.append({"timestamp_seconds": round(timestamp, 3), "analysis": answer.get("text", "")})
        return {"success": True, "mode": "sampled_frame_analysis_not_full_temporal_understanding",
                "frame_count": len(frames), "duration_seconds": round(duration, 3), "frames": frames,
                "model": self.vision.model}


class TextToVideoAdapter:
    """Contract for a separately installed, explicitly local text-to-video model."""
    name = "self-hosted-text-to-video"

    def __init__(self, backend=None):
        self.backend = backend

    def capabilities(self) -> dict:
        available = bool(self.backend and getattr(self.backend, "local_only", False)
                         and callable(getattr(self.backend, "generate_video", None)))
        return {"name": self.name, "enabled": available,
                "operations": ["text_to_video"] if available else [],
                "mode": "neural_text_to_video" if available else "unavailable",
                "policy": "separate local model integration; storyboard/slideshow is not text-to-video"}

    def execute(self, operation: str, payload: dict) -> dict:
        if operation != "text_to_video" or not self.capabilities()["enabled"]:
            raise RuntimeError("Ayrı yerel metinden video modeli yapılandırılmamış.")
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt or len(prompt) > 2000:
            raise RuntimeError("Video istemi 1 ile 2000 karakter arasında olmalıdır.")
        duration = float(payload.get("duration_seconds", 4))
        if not 1 <= duration <= 20:
            raise RuntimeError("Video süresi 1 ile 20 saniye arasında olmalıdır.")
        return self.backend.generate_video(prompt=prompt, duration_seconds=duration)


class ImageGeneratorAdapter:
    """Adapter for the existing local-only Stable Diffusion/ffmpeg implementation."""
    name = "self-hosted-image-generator"

    def __init__(self, generator):
        self.generator = generator

    def capabilities(self) -> dict:
        configured = bool(getattr(self.generator, "sd_url", ""))
        return {
            "name": self.name,
            "enabled": configured,
            "backend_configured": configured,
            "operations": ["generate", "edit", "background", "video", "story_video"] if configured else [],
            "mode": "local_neural_image_and_storyboard_video" if configured else "unavailable",
            "policy": "self-hosted only; no public fallback; configuration is not a runtime health check",
        }

    def execute(self, operation: str, payload: dict) -> dict:
        if operation == "generate":
            return self.generator.generate(
                payload.get("prompt", ""),
                width=payload.get("width", 768),
                height=payload.get("height", 768),
            )
        if operation in {"edit", "background"}:
            image_bytes = payload.get("image_bytes")
            image_path = payload.get("image_path")
            if image_bytes is None and image_path:
                from pathlib import Path

                root = Path("./memory/uploads").resolve()
                source = Path(str(image_path)).resolve()
                if root not in source.parents or not source.is_file():
                    raise RuntimeError("Kuyruk görsel dosyası izin verilen yerel yükleme dizininde değil.")
                image_bytes = source.read_bytes()
            if operation == "edit":
                return self.generator.edit(payload.get("prompt", ""), image_bytes or b"")
            return self.generator.replace_background(
                image_bytes or b"", payload.get("color", "#172033")
            )
        if operation == "video":
            return self.generator.create_video(
                payload.get("filename", ""), payload.get("duration", 4.0)
            )
        if operation == "story_video":
            return self.generator.create_story_video(
                payload.get("prompts", []), payload.get("duration", 8.0)
            )
        raise RuntimeError("Medya işlemi desteklenmiyor.")
