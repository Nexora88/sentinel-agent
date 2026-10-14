"""
Image Generation for Sentinel.

Priority:
1. Local Stable Diffusion / Automatic1111 / ComfyUI (SD_API_URL)
2. Free Pollinations.ai (no key required)
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger("sentinel.image_gen")


class ImageGenerator:
    def __init__(self, output_dir: str = "./memory/generated_images"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sd_url = os.getenv("SD_API_URL", "").rstrip("/")  # e.g. http://localhost:7860

    def generate(self, prompt: str, negative: str = "", width: int = 768, height: int = 768) -> dict:
        """Generate image, save locally, return path + url info."""
        prompt = prompt.strip()
        if not prompt:
            return {"error": "Prompt boş"}

        # 1) Local Stable Diffusion (A1111 API)
        if self.sd_url:
            try:
                payload = {
                    "prompt": prompt,
                    "negative_prompt": negative or "low quality, blurry, distorted",
                    "width": width,
                    "height": height,
                    "steps": 25,
                    "cfg_scale": 7,
                }
                r = requests.post(f"{self.sd_url}/sdapi/v1/txt2img", json=payload, timeout=120)
                r.raise_for_status()
                data = r.json()
                import base64
                img_b64 = data["images"][0]
                filename = f"sd_{uuid.uuid4().hex[:10]}.png"
                path = self.output_dir / filename
                path.write_bytes(base64.b64decode(img_b64))
                return {
                    "success": True,
                    "path": str(path),
                    "filename": filename,
                    "source": "local_sd",
                    "prompt": prompt,
                }
            except Exception as e:
                logger.warning(f"Local SD failed, falling back: {e}")

        # 2) Free Pollinations.ai (no API key)
        try:
            # Pollinations returns image directly
            encoded = requests.utils.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true"
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            filename = f"poll_{uuid.uuid4().hex[:10]}.jpg"
            path = self.output_dir / filename
            path.write_bytes(r.content)
            return {
                "success": True,
                "path": str(path),
                "filename": filename,
                "source": "pollinations",
                "prompt": prompt,
                "url": url,  # also viewable online
            }
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {"error": str(e), "prompt": prompt}
