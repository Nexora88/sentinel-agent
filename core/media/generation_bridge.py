"""Model-independent media bridge. Adapters must be explicitly local/self-hosted."""
from __future__ import annotations
from typing import Any, Protocol

class MediaAdapter(Protocol):
    name: str
    def capabilities(self) -> dict: ...
    def execute(self, operation: str, payload: dict) -> dict: ...

class GenerationBridge:
    def __init__(self, adapters: list[MediaAdapter] | None = None):
        self.adapters = adapters or []

    def capabilities(self) -> dict:
        return {"adapter_count": len(self.adapters), "adapters": [a.capabilities() for a in self.adapters],
                "policy": "explicit adapters only; no public API fallback"}

    def execute(self, operation: str, payload: dict) -> dict:
        for adapter in self.adapters:
            caps = adapter.capabilities()
            if caps.get("enabled") and operation in caps.get("operations", []):
                return adapter.execute(operation, payload)
        raise RuntimeError("Bu işlem için etkin, açıkça yapılandırılmış yerel model adaptörü yok; dış servise gönderilmedi.")

class ImageGeneratorAdapter:
    """Adapter for the existing local-only Stable Diffusion/ffmpeg implementation."""
    name = "self-hosted-image-generator"
    def __init__(self, generator):
        self.generator = generator
    def capabilities(self) -> dict:
        configured = bool(getattr(self.generator, "sd_url", ""))
        return {"name": self.name, "enabled": True, "backend_configured": configured,
                "operations": ["generate", "edit", "background", "video"],
                "policy": "self-hosted only; no public fallback"}
    def execute(self, operation: str, payload: dict) -> dict:
        if operation == "generate":
            return self.generator.generate(payload.get("prompt", ""), width=payload.get("width",768), height=payload.get("height",768))
        if operation == "edit":
            return self.generator.edit(payload.get("prompt", ""), payload.get("image_bytes", b""))
        if operation == "background":
            return self.generator.replace_background(payload.get("image_bytes", b""), payload.get("color", "#172033"))
        if operation == "video":
            return self.generator.create_video(payload.get("filename", ""), payload.get("duration", 4.0))
        if operation == "report_infographic":
            raise RuntimeError("Rapor infografiği adaptörü henüz etkin değil.")
        raise RuntimeError("Medya işlemi desteklenmiyor.")
