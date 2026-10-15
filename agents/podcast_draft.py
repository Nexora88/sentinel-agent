"""
Podcast metni taslağı — Night Research çıktısından.
Yalnızca yerel metin üretir; yayın / Substack / Spotify yok.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from core.ollama_client import OllamaClient

logger = logging.getLogger("sentinel.podcast_draft")


class PodcastDraft:
    def __init__(self, ollama: Optional[OllamaClient] = None):
        self.ollama = ollama or OllamaClient()
        self.out_dir = Path("./memory/podcast_drafts")
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def from_night_summary(self, summary: str, title_hint: str = "") -> Dict[str, Any]:
        summary = (summary or "").strip()
        if len(summary) < 40:
            return {"success": False, "error": "Özet çok kısa — önce night research çalıştır."}

        prompt = f"""Aşağıdaki gece araştırma raporundan TÜRKÇE bir podcast bölümü METİN TASLAĞI yaz.

Kurallar:
- Sadece konuşma metni (sunucu monoloğu + kısa bölüm başlıkları)
- Süre hedefi ~6-10 dakika okuma
- Giriş, 3 ana bölüm, kapanış
- Tıbbi teşhis / yatırım tavsiyesi / "hemen al" dili YOK
- Teknik, sakin, bilgilendirici ton
- Otomatik yayın yok; bu sadece taslak

Başlık ipucu: {title_hint or "Sentinel Gece Raporu"}

Rapor:
{summary[:12000]}

Podcast metni:"""

        try:
            script = self.ollama.chat(
                prompt,
                system=(
                    "Türkçe podcast senaristisin. Sadece metin taslağı üret. "
                    "Yayın komutu, API çağrısı veya dış servis önerme."
                ),
            ).strip()
        except Exception as e:
            logger.error(f"Podcast draft failed: {e}")
            return {"success": False, "error": str(e)}

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
        path = self.out_dir / f"podcast_{ts}.md"
        body = (
            f"# Podcast Taslağı — {ts}\n\n"
            f"> Otomatik yayın YOK. Sadece yerel taslak.\n\n"
            f"{script}\n"
        )
        path.write_text(body, encoding="utf-8")

        return {
            "success": True,
            "path": str(path),
            "script": script[:20000],
            "chars": len(script),
        }

    def from_latest_night_report(self) -> Dict[str, Any]:
        reports = sorted(Path("./memory/night_reports").glob("night_*.md"))
        if not reports:
            return {"success": False, "error": "Henüz night raporu yok. Önce Gece Araştırması çalıştır."}
        latest = reports[-1]
        text = latest.read_text(encoding="utf-8", errors="ignore")
        result = self.from_night_summary(text, title_hint=latest.stem)
        result["source_report"] = str(latest)
        return result
