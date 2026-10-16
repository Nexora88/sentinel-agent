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


class ImageGeneratorAdapter:
    """Adapter for the existing local-only Stable Diffusion/ffmpeg implementation."""
    name = "self-hosted-image-generator"

    def __init__(self, generator):
        self.generator = generator

    def capabilities(self) -> dict:
        configured = bool(getattr(self.generator, "sd_url", ""))
        return {
            "name": self.name,
            "enabled": True,
            "backend_configured": configured,
            "operations": ["generate", "edit", "background", "video", "story_video"],
            "policy": "self-hosted only; no public fallback",
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
