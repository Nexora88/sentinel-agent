"""
Document assistant — extract dates, amounts, reference numbers from text.
Suggestions only. NEVER initiates payments or bank transfers.
"""

from __future__ import annotations

import re
from typing import Dict, List

from core.ollama_client import OllamaClient

DATE_RE = re.compile(
    r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b",
    re.I,
)
MONEY_RE = re.compile(r"\b(?:TRY|TL|USD|EUR|\$|€|₺)\s?(\d+[.,]\d{2}|\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\b")


class DocumentAssistant:
    def __init__(self, ollama: OllamaClient | None = None):
        self.ollama = ollama or OllamaClient()

    def analyze_text(self, text: str) -> Dict:
        text = (text or "")[:15000]
        dates = list(dict.fromkeys(DATE_RE.findall(text)))[:20]
        # money regex groups differently — simplify
        amounts = list(dict.fromkeys(m.group(0) for m in re.finditer(
            r"(?:TRY|TL|USD|EUR|\$|€|₺)\s?\d+[\d.,]*", text, re.I
        )))[:20]

        summary = ""
        try:
            summary = self.ollama.chat(
                f"Aşağıdaki belge metninden: belge türü, son ödeme/teslim tarihi adayları, "
                f"tutar adayları ve 3 ajanda notu çıkar. Ödeme emri VERME.\n\n{text[:8000]}",
                system="Belge asistanı. Sadece özet ve öneri. Finansal işlem başlatma.",
            )
        except Exception as e:
            summary = f"(LLM özet yok: {e})"

        return {
            "dates_found": dates,
            "amounts_found": amounts,
            "summary": summary[:3000],
            "warning": "Öneriler bilgilendirme içindir. Otomatik ödeme YOK.",
        }

    def format_report(self, result: Dict) -> str:
        lines = [
            "📄 Belge asistanı (sadece öneri)",
            result.get("warning", ""),
            f"Tarihler: {', '.join(result.get('dates_found') or ['—'])}",
            f"Tutarlar: {', '.join(result.get('amounts_found') or ['—'])}",
            "",
            result.get("summary", ""),
        ]
        return "\n".join(lines)
