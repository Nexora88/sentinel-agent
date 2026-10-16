"""MKAOS dil politikası — varsayılan Türkçe, egemen yanıt çerçevesi.

Bu modül model kalitesini kanıtlamaz; istem şablonunu ve eğitim dili
etiketlerini tutarlı tutar.
"""
from __future__ import annotations

import re
from typing import Iterable

DEFAULT_LANGUAGE = "tr"
RESPONSE_LOCALE = "tr-TR"

SYSTEM_FRAME_TR = (
    "Sen MKAOS'sun: yerel, Türkçe öncelikli araştırma asistanısın. "
    "Yanıtlarını açık, doğru ve Türkçe ver. Bilmediğin yerde uydurma; "
    "belirsizliği belirt. Üçüncü taraf bulut API'sine bağlanma."
)

CHAT_TEMPLATE_TR = (
    "Sistem: {system}\n"
    "Kullanıcı: {user}\n"
    "MKAOS:"
)


def wrap_user_prompt(user_text: str, *, system: str | None = None) -> str:
    """Yerel üreticiye gidecek Türkçe çerçeveli istem."""
    text = (user_text or "").strip()
    if not text:
        raise ValueError("boş kullanıcı metni")
    return CHAT_TEMPLATE_TR.format(system=system or SYSTEM_FRAME_TR, user=text)


def is_mostly_turkish(text: str, *, min_ratio: float = 0.35) -> bool:
    """Kaba sezgisel kontrol: Latin harf içinde Türkçe özel karakter veya yaygın sözcük."""
    if not text or not text.strip():
        return False
    letters = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", text)
    if not letters:
        return False
    tr_special = sum(1 for c in letters if c in "ÇĞİÖŞÜçğıöşü")
    # Also accept pure ASCII Turkish common words without diacritics
    lower = text.lower()
    common = (
        " ve ", " bir ", " bu ", " için ", " değil", " ile ", " olan ",
        "türk", "ankara", "istanbul", "cumhuriyet", "merhaba",
    )
    has_common = any(w in f" {lower} " for w in common)
    ratio = tr_special / max(1, len(letters))
    return ratio >= min_ratio or has_common


def assert_turkish_training_records(records: Iterable[dict]) -> list[str]:
    """Eğitim kayıtlarında Türkçe içerik yoksa hata listesi döndür."""
    errors: list[str] = []
    for i, row in enumerate(records):
        prompt = str(row.get("prompt", ""))
        response = str(row.get("response", ""))
        if not is_mostly_turkish(prompt) and not is_mostly_turkish(response):
            errors.append(f"records[{i}] ({row.get('source_id')}): Türkçe içerik sezilmedi")
        lang = row.get("language") or row.get("lang")
        if lang is not None and str(lang).lower() not in {"tr", "tr-tr", "turkish", "türkçe"}:
            errors.append(f"records[{i}]: language etiketi Türkçe değil: {lang!r}")
    return errors
