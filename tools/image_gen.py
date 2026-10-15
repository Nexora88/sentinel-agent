"""Local-first image and media tools for MKAOS.

Only an explicitly configured self-hosted Stable Diffusion WebUI endpoint is used.
There is no public image API fallback. Background removal is optional (rembg with a
pre-downloaded local model); video rendering uses local ffmpeg.
"""
from __future__ import annotations
import base64, ipaddress, logging, os, re, shutil, subprocess, uuid
from pathlib import Path
from urllib.parse import urlparse
import requests

logger = logging.getLogger("mkaos.media")

class MediaToolError(RuntimeError):
    """Expected, user-displayable media processing error."""

class ImageGenerator:
    def __init__(self, output_dir: str = "./memory/generated_images"):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sd_url = os.getenv("SD_API_URL", "").strip().rstrip("/")
        self._validate_endpoint_if_set()

    def _validate_endpoint_if_set(self):
        if not self.sd_url:
            return
        parsed = urlparse(self.sd_url)
        host = parsed.hostname or ""
        if parsed.scheme != "http" or not host or parsed.username or parsed.password:
            raise MediaToolError("SD_API_URL yalnızca kimlik bilgisiz HTTP yerel uç noktası olabilir.")
        allowed = host.lower() in {"localhost", "host.docker.internal"} or "." not in host
        try:
            ip = ipaddress.ip_address(host)
            allowed = ip.is_loopback or ip.is_private or ip.is_link_local
        except ValueError:
            pass
        if not allowed:
            raise MediaToolError("SD_API_URL dış alan adına izin verilmiyor; kendi yönettiğin model sunucusunu kullan.")

    def _require_backend(self):
        if not self.sd_url:
            raise MediaToolError("Yerel görsel motoru bağlı değil. Kendi makine/bulut sunucunda Stable Diffusion WebUI API'yi açıp SD_API_URL ayarla. Dış görsel servisine veri gönderilmedi.")
        return self.sd_url

    def _save_b64_image(self, encoded: str, prefix: str, prompt: str = "") -> dict:
        """Validate, decode and normalize model output to a clean PNG atomically."""
        try:
            raw = base64.b64decode(encoded, validate=True)
            if not raw or len(raw) > 25 * 1024 * 1024:
                raise MediaToolError("Model çıktısı boş veya 25 MB sınırını aşıyor.")
            from PIL import Image
            import io
            with Image.open(io.BytesIO(raw)) as image:
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                if image.width * image.height > 20_000_000:
                    raise MediaToolError("Model çıktısı 20 megapiksel sınırını aşıyor.")
                # Decode pixels and re-encode rather than trusting the source container,
                # extension, metadata or ancillary chunks returned by the model.
                image.load()
                normalized = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                buffer = io.BytesIO()
                normalized.save(buffer, format="PNG", optimize=True)
                clean_png = buffer.getvalue()
            if not clean_png or len(clean_png) > 25 * 1024 * 1024:
                raise MediaToolError("Temizlenmiş görsel boş veya 25 MB sınırını aşıyor.")
        except MediaToolError:
            raise
        except Exception as exc:
            raise MediaToolError("Model geçerli bir görsel döndürmedi.") from exc

        filename = f"{prefix}_{uuid.uuid4().hex[:12]}.png"
        target = self.output_dir / filename
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=str(self.output_dir), prefix=".image-", suffix=".tmp", delete=False
            ) as handle:
                temp_name = handle.name
                handle.write(clean_png)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temp_name, 0o600)
            except OSError:
                pass
            os.replace(temp_name, target)
            try:
                os.chmod(target, 0o600)
            except OSError:
                pass
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
        return {"success": True, "filename": filename, "source": "self_hosted_sd", "prompt": prompt}

    def _image_response(self, endpoint: str, payload: dict, prefix: str, prompt: str = "") -> dict:
        try:
            with requests.Session() as session:
                session.trust_env = False
                response = session.post(self._require_backend() + endpoint, json=payload, timeout=(5, 180), allow_redirects=False)
            response.raise_for_status()
            images = response.json().get("images", [])
            if not images or not isinstance(images[0], str):
                raise MediaToolError("Yerel model görsel üretmedi; model/VRAM durumunu denetle.")
            return self._save_b64_image(images[0], prefix, prompt)
        except MediaToolError:
            raise
        except requests.RequestException as exc:
            logger.warning("Self-hosted image endpoint failed: %s", type(exc).__name__)
            raise MediaToolError("Yerel görsel motoruna ulaşılamadı. SD_API_URL ve model sunucusunu kontrol et.") from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise MediaToolError("Yerel görsel motorunun yanıtı çözümlenemedi.") from exc

    @staticmethod
    def _read_image(image_bytes: bytes):
        if not image_bytes or len(image_bytes) > 12 * 1024 * 1024:
            raise MediaToolError("Görsel boş veya 12 MB sınırını aşıyor.")
        try:
            from PIL import Image
            import io
            image = Image.open(io.BytesIO(image_bytes))
            image.verify()
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            if image.width * image.height > 20_000_000:
                raise MediaToolError("Görsel çözünürlüğü çok yüksek (20 megapiksel üstü).")
            return image
        except MediaToolError:
            raise
        except Exception as exc:
            raise MediaToolError("Desteklenmeyen veya bozuk görsel dosyası.") from exc

    def generate(self, prompt: str, negative: str = "", width: int = 768, height: int = 768) -> dict:
        prompt = str(prompt or "").strip()
        if not prompt:
            raise MediaToolError("Görsel tarifi boş.")
        width, height = max(256, min(1024, int(width))), max(256, min(1024, int(height)))
        return self._image_response("/sdapi/v1/txt2img", {
            "prompt": prompt[:2000],
            "negative_prompt": str(negative or "low quality, blurry, distorted")[:1000],
            "width": width - width % 8, "height": height - height % 8,
            "steps": 25, "cfg_scale": 7,
        }, "mkaos", prompt)

    def edit(self, prompt: str, image_bytes: bytes, strength: float = 0.55) -> dict:
        prompt = str(prompt or "").strip()
        if not prompt:
            raise MediaToolError("Düzenleme açıklaması boş.")
        image = self._read_image(image_bytes)
        import io
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return self._image_response("/sdapi/v1/img2img", {
            "prompt": prompt[:2000], "negative_prompt": "low quality, blurry, malformed",
            "init_images": [base64.b64encode(buffer.getvalue()).decode("ascii")],
            "denoising_strength": max(0.1, min(0.9, float(strength))),
            "steps": 25, "cfg_scale": 7,
            "width": max(256, min(1024, image.width - image.width % 8)),
            "height": max(256, min(1024, image.height - image.height % 8)),
        }, "edit", prompt)

    def replace_background(self, image_bytes: bytes, color: str = "#172033") -> dict:
        image = self._read_image(image_bytes)
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(color or "")):
            raise MediaToolError("Arka plan rengi #RRGGBB biçiminde olmalı.")
        model_home = Path(os.getenv("U2NET_HOME", str(Path.home() / ".u2net"))).expanduser()
        if not (model_home / "u2net.onnx").is_file():
            raise MediaToolError("Yerel arka plan modeli yok. rembg ve u2net.onnx önceden kurulmalı; otomatik indirme yapılmaz.")
        try:
            from rembg import remove
            import io
            source = io.BytesIO()
            image.save(source, format="PNG")
            cutout = self._read_rgba(remove(source.getvalue()))
            rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
            from PIL import Image
            background = Image.new("RGBA", cutout.size, (*rgb, 255))
            background.alpha_composite(cutout)
            output = self.output_dir / f"background_{uuid.uuid4().hex[:12]}.png"
            background.save(output, format="PNG")
            return {"success": True, "filename": output.name, "source": "local_rembg", "prompt": "Arka plan değiştirildi"}
        except MediaToolError:
            raise
        except Exception as exc:
            logger.warning("Local background replacement failed: %s", type(exc).__name__)
            raise MediaToolError("Yerel arka plan ayırma başarısız oldu; rembg/u2net modelini denetle.") from exc

    @staticmethod
    def _read_rgba(raw: bytes):
        from PIL import Image
        import io
        return Image.open(io.BytesIO(raw)).convert("RGBA")

    def create_story_video(self, prompts: list[str], duration: float = 8.0) -> dict:
        """Create a local storyboard video from 2-6 AI-generated keyframes.

        This is a scene-by-scene storyboard, not neural text-to-video. Each frame
        is generated by the explicitly configured self-hosted Stable Diffusion endpoint.
        """
        if not isinstance(prompts, list) or not 2 <= len(prompts) <= 6:
            raise MediaToolError("Storyboard için 2-6 sahne açıklaması gerekli.")
        clean_prompts = []
        for item in prompts:
            prompt = str(item or "").strip()
            if not prompt or len(prompt) > 1000:
                raise MediaToolError("Her sahne açıklaması 1-1000 karakter olmalı.")
            clean_prompts.append(prompt)
        duration = max(4.0, min(24.0, float(duration)))
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise MediaToolError("Yerel storyboard videosu için ffmpeg kurulu olmalı.")

        frames = []
        manifest = None
        target = self.output_dir / f"story_{uuid.uuid4().hex[:12]}.mp4"
        try:
            for prompt in clean_prompts:
                result = self.generate(prompt, width=768, height=432)
                filename = result.get("filename", "")
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}\.png", filename):
                    raise MediaToolError("Yerel model güvenli bir kare dosyası döndürmedi.")
                frame = (self.output_dir / filename).resolve()
                if self.output_dir not in frame.parents or not frame.is_file():
                    raise MediaToolError("Oluşturulan storyboard karesi bulunamadı.")
                frames.append(frame)

            import tempfile
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt",
                                             dir=str(self.output_dir), delete=False) as handle:
                manifest = Path(handle.name)
                for frame in frames:
                    escaped = str(frame).replace("'", "'\\''")
                    handle.write(f"file '{escaped}'\n")
                    handle.write(f"duration {duration / len(frames):.4f}\n")
                handle.write(f"file '{str(frames[-1]).replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n")
            try:
                os.chmod(manifest, 0o600)
            except OSError:
                pass
            completed = subprocess.run(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
                 "-safe", "0", "-i", str(manifest), "-vf",
                 "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=24,format=yuv420p",
                 "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(target)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180, check=False,
            )
            if completed.returncode != 0 or not target.is_file() or target.stat().st_size == 0:
                target.unlink(missing_ok=True)
                raise MediaToolError("Storyboard kodlanamadı; ffmpeg/libx264 kurulumunu denetle.")
            return {"success": True, "filename": target.name, "source": "local_sd_storyboard_ffmpeg",
                    "duration": duration, "scene_count": len(frames),
                    "mode": "AI-generated keyframe storyboard; not neural text-to-video"}
        except MediaToolError:
            raise
        except Exception as exc:
            target.unlink(missing_ok=True)
            logger.warning("Local storyboard video failed: %s", type(exc).__name__)
            raise MediaToolError("Yerel storyboard videosu oluşturulamadı; model ve ffmpeg durumunu denetle.") from exc
        finally:
            if manifest:
                manifest.unlink(missing_ok=True)

    def create_video(self, filename: str, duration: float = 4.0) -> dict:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}\.png", str(filename or "")):
            raise MediaToolError("Video için güvenli PNG dosya adı gerekli.")
        source = (self.output_dir / filename).resolve()
        if self.output_dir not in source.parents or not source.is_file():
            raise MediaToolError("Kaynak görsel bulunamadı.")
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise MediaToolError("Yerel video oluşturmak için ffmpeg kurulu olmalı.")
        duration = max(2.0, min(8.0, float(duration)))
        target = self.output_dir / f"motion_{uuid.uuid4().hex[:12]}.mp4"
        vf = "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,zoompan=z='min(zoom+0.001,1.06)':d=1:s=1280x720:fps=24,format=yuv420p"
        result = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", str(source),
            "-vf", vf, "-t", str(duration), "-r", "24", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(target)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90, check=False)
        if result.returncode != 0 or not target.is_file() or target.stat().st_size == 0:
            target.unlink(missing_ok=True)
            raise MediaToolError("Yerel video oluşturulamadı; ffmpeg/libx264 kurulumunu denetle.")
        return {"success": True, "filename": target.name, "source": "local_ffmpeg", "duration": duration}
