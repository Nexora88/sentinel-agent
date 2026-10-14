"""
Personal Assistant — The main conversational brain.
Knows the user, routes commands to specialized agents, stays private.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from core.ollama_client import OllamaClient
from core.personal_memory import PersonalMemory
from core.permission_manager import PermissionManager, Action

logger = logging.getLogger("sentinel.personal_assistant")

SYSTEM_PROMPT = """Sen Sentinel'sin. Kullanıcının özel, gizli ve süper zeki kişisel AI ajanısın.
Tamamen self-hosted çalışıyorsun (Ollama). Hiçbir veri dışarı çıkmaz.

Görevin:
- Kullanıcıyı tanımak, tercihlerini ve projelerini hatırlamak
- Doğal dilde komutları anlamak ve ilgili araçları/ajanları kullanmak
- Kod inceleme, hata ayıklama, güvenlik taraması, dosya düzeltme gibi işleri yapmak
- Her zaman izin modeline uymak: yazma / commit / push işlemlerinde onay beklemek
- Kısa, net, Türkçe cevap vermek (kullanıcı başka dil istemedikçe)
- Kendini geliştirmek ve kullanıcıya özel olmak

Kullanıcı profili ve hafıza aşağıda verilecek. Bunu kullanarak kişiselleştir.

Önemli kurallar:
- Asla otomatik commit/push yapma
- Sadece defensive güvenlik yap (saldırı amaçlı kod üretme)
- Bilmediğin şeyi uydurma, söyle
- Komutları anla: "repo tara", "şu hatayı düzelt", "sitene bak", "bana öğret" vb.
"""


class PersonalAssistant:
    def __init__(
        self,
        ollama: Optional[OllamaClient] = None,
        memory: Optional[PersonalMemory] = None,
        permissions: Optional[PermissionManager] = None,
        pipeline=None,  # SentinelPipeline reference for tool use
    ):
        self.ollama = ollama or OllamaClient()
        self.memory = memory or PersonalMemory(ollama=self.ollama)
        self.permissions = permissions or PermissionManager()
        self.pipeline = pipeline

    def _build_prompt(self, user_message: str) -> str:
        context = self.memory.get_context_for_prompt(user_message)
        return f"""{SYSTEM_PROMPT}

### Kullanıcı Hakkında Bilinenler
{context}

### Kullanıcı Mesajı
{user_message}

### Cevabın
Kısa, yardımcı ve eylem odaklı ol. Gerekirse hangi aracı kullanacağını belirt.
"""

    def chat(self, user_message: str) -> str:
        """Main entry point for conversation."""
        user_message = user_message.strip()
        if not user_message:
            return "Mesaj boş geldi."

        # Quick command routing (before full LLM for speed & reliability)
        lower = user_message.lower()

        # Identity / learning
        if any(x in lower for x in ["adım", "ismim", "benim adım"]):
            # Extract possible name
            match = re.search(r"(?:adım|ismim|benim adım)\s+([A-Za-zÇĞİÖŞÜçğıöşü\s]+)", user_message, re.I)
            if match:
                name = match.group(1).strip()
                self.memory.set_name(name)
                return f"Anladım, seni {name} olarak hatırlayacağım."

        # Explicit learn
        if lower.startswith("öğren:") or lower.startswith("hatırla:"):
            fact = user_message.split(":", 1)[1].strip()
            self.memory.add_fact(fact)
            return f"Kaydettim: {fact}"

        # Route to specialized tools if clear intent
        if self.pipeline:
            if any(kw in lower for kw in ["repo tara", "repo incele", "kod incele", "review repo"]):
                # Expect URL or use watched
                return (
                    "Repo taraması için şu komutu kullan:\n"
                    "`repo https://github.com/kullanici/proje.git`\n"
                    "veya CLI'dan: python -m scripts.run repo <url>"
                )

            if "debug" in lower or "hata" in lower or "error" in lower:
                # Let LLM handle, or extract
                pass

            if any(kw in lower for kw in ["site tara", "website tara", "güvenlik tara", "açık ara"]):
                url_match = re.search(r"https?://[^\s]+", user_message)
                if url_match:
                    url = url_match.group(0)
                    return self.pipeline.scan_website(url)

        # Full LLM response with personal context
        prompt = self._build_prompt(user_message)
        try:
            reply = self.ollama.chat(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ]
            )
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            reply = f"Şu an model cevap veremedi: {e}"

        # Learn from this turn
        self.memory.extract_and_learn(user_message, reply)

        return reply

    def get_status(self) -> str:
        p = self.memory.profile
        name = p.get("name") or "Henüz isim bilinmiyor"
        facts = len(p.get("facts", []))
        projects = ", ".join(p.get("projects", [])[-3:]) or "-"
        return (
            f"🧠 Sentinel Hazır\n"
            f"Sahip: {name}\n"
            f"Bilinen gerçek: {facts}\n"
            f"Projeler: {projects}\n"
            f"İzin modeli: aktif (yazma için onay gerekir)"
        )
