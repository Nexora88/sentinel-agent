"""Bulutsuz yerel görsel / kısa video üretimi.

- PNG poster ve diyagram: Pillow (ağ yok)
- Kısa slideshow MP4: yerel ffmpeg (SD model zorunlu değil)
Stable Diffusion yalnızca açıkça SD_API_URL ayarlıysa ayrı adaptörle kullanılır.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import textwrap
import uuid
from datetime import datetime
from pathlib import Path
from typing import Sequence


class LocalCanvasError(RuntimeError):
    pass


class LocalCanvas:
    def __init__(self, output_dir: str | Path = "./memory/generated_images"):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _name(self, prefix: str, ext: str) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"{prefix}_{stamp}_{uuid.uuid4().hex[:8]}.{ext}"

    def poster(
        self,
        title: str,
        body: str,
        *,
        width: int = 1280,
        height: int = 720,
        accent: tuple[int, int, int] = (20, 184, 166),
    ) -> dict:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError as exc:
            raise LocalCanvasError("Pillow kurulu değil (yerel çizim).") from exc

        img = Image.new("RGB", (width, height), (8, 17, 33))
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, width, 16), fill=accent)
        font = ImageFont.load_default()
        draw.text((48, 48), "MKAOS YEREL STÜDYO", fill=accent, font=font)
        draw.text((48, 88), (title or "Başlıksız")[:120], fill=(241, 245, 249), font=font)
        y = 140
        for paragraph in str(body or "").splitlines() or [""]:
            for line in textwrap.wrap(paragraph, width=90) or [""]:
                draw.text((48, y), line[:140], fill=(203, 213, 225), font=font)
                y += 22
                if y > height - 80:
                    break
        draw.text(
            (48, height - 40),
            "YEREL · AĞ YOK · İNCELEME SONRASI KULLAN",
            fill=(251, 191, 36),
            font=font,
        )
        path = self._name("poster", "png")
        img.save(path, format="PNG", optimize=True)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return {
            "success": True,
            "path": str(path),
            "filename": path.name,
            "sha256": digest,
            "source": "local_pillow_poster",
            "network": False,
        }

    def code_card(self, language: str, snippet: str, title: str = "Kod") -> dict:
        body = f"{language}\n\n{snippet[:3500]}"
        return self.poster(title=title, body=body, accent=(99, 102, 241))

    def slideshow(
        self,
        image_paths: Sequence[str | Path],
        *,
        duration_per_frame: float = 2.0,
        fps: int = 30,
    ) -> dict:
        """Yerel PNG'lerden kısa MP4. ffmpeg gerekir; model indirmez."""
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise LocalCanvasError("ffmpeg bulunamadı; slideshow üretilemedi.")
        frames = []
        for p in image_paths:
            path = Path(p).resolve()
            if not path.is_file() or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                raise LocalCanvasError(f"geçersiz kare: {p}")
            if self.output_dir not in path.parents and path.parent != self.output_dir:
                # only allow under output_dir or explicit generated path
                if "generated_images" not in path.parts and "uploads" not in path.parts:
                    raise LocalCanvasError("kare izin verilen medya dizininde değil")
            frames.append(path)
        if not frames:
            raise LocalCanvasError("kare yok")

        list_file = self.output_dir / f"concat_{uuid.uuid4().hex[:10]}.txt"
        lines = []
        for frame in frames:
            lines.append(f"file '{frame.as_posix()}'")
            lines.append(f"duration {max(0.5, min(duration_per_frame, 8.0))}")
        lines.append(f"file '{frames[-1].as_posix()}'")
        list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        out = self._name("slideshow", "mp4")
        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-vsync",
            "vfr",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(max(1, min(fps, 60))),
            str(out),
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        finally:
            try:
                list_file.unlink(missing_ok=True)
            except OSError:
                pass
        if proc.returncode != 0 or not out.is_file():
            raise LocalCanvasError(
                "ffmpeg slideshow başarısız: " + (proc.stderr or "")[:400]
            )
        return {
            "success": True,
            "path": str(out),
            "filename": out.name,
            "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
            "frames": len(frames),
            "source": "local_ffmpeg_slideshow",
            "network": False,
        }
