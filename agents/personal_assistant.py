"""
Personal Assistant — Aggressive tool-calling brain.
Knows the user, autonomously routes to tools, learns continuously.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from core.ollama_client import OllamaClient
from core.personal_memory import PersonalMemory
from core.permission_manager import PermissionManager, Action

logger = logging.getLogger("sentinel.personal_assistant")

SYSTEM_PROMPT = """Sen Sentinel'sin — kullanıcının özel, gizli, sürekli gelişen kişisel AI ajanısın.
Self-hosted (Ollama). Veri dışarı çıkmaz.

Yetkinliklerin:
- Kod inceleme, debug, güvenlik taraması, dosya düzeltme
- GitHub: repo listele, dosya yaz, commit/push (izinli), issue/PR aç
- Finans: hisse, kripto, piyasa analizi
- Görsel üretimi
- Bilgi evrenini genişletme (internetten öğrenme)
- Website defensive tarama
- Kullanıcıyı tanıma ve hatırlama

Kurallar:
- Yazma / push / PR işlemlerinde ASLA otomatik yapma, onay iste
- Sadece defensive güvenlik
- Kısa, net, eylem odaklı Türkçe cevap ver
- Araç kullanman gerektiğinde direkt kullan, sadece konuşma
"""


class PersonalAssistant:
    def __init__(
        self,
        ollama: Optional[OllamaClient] = None,
        memory: Optional[PersonalMemory] = None,
        permissions: Optional[PermissionManager] = None,
        pipeline=None,
    ):
        self.ollama = ollama or OllamaClient()
        self.memory = memory or PersonalMemory(ollama=self.ollama)
        self.permissions = permissions or PermissionManager()
        self.pipeline = pipeline

    def _try_tools(self, message: str) -> Optional[str]:
        """Aggressive intent detection + tool execution. Returns reply or None."""
        if not self.pipeline:
            return None

        lower = message.lower().strip()

        # --- Identity ---
        if any(x in lower for x in ["adım", "ismim", "benim adım"]):
            match = re.search(r"(?:adım|ismim|benim adım)\s+([A-Za-zÇĞİÖŞÜçğıöşü\s]+)", message, re.I)
            if match:
                name = match.group(1).strip()
                self.memory.set_name(name)
                return f"Anladım, seni **{name}** olarak kaydettim."

        if lower.startswith(("öğren:", "hatırla:", "öğren ", "hatırla ")):
            fact = re.split(r"[: ]", message, 1)[-1].strip()
            if fact:
                self.memory.add_fact(fact)
                return f"✅ Kaydettim: {fact}"

        # --- Website scan ---
        if any(k in lower for k in ["site tara", "website tara", "güvenlik tara", "açık ara", "scan site"]):
            url_m = re.search(r"https?://[^\s]+", message)
            if url_m:
                return self.pipeline.scan_website(url_m.group(0))

        # --- Debug ---
        if any(k in lower for k in ["debug", "hata ayıkla", "şu hatayı", "error:"]):
            # Extract error-like text
            return self.pipeline.debug_error(message)

        # --- Knowledge expand ---
        if any(k in lower for k in ["genişlet", "öğren internet", "bilgi evreni", "expand knowledge", "daha fazla öğren"]):
            topic = None
            m = re.search(r"(?:konu|topic)[:= ]+(.+)", message, re.I)
            if m:
                topic = m.group(1).strip()
            result = self.pipeline.expand_knowledge(topic=topic)
            return (
                f"🌌 Bilgi evreni genişledi.\n"
                f"Konu: {result.get('topic')}\n"
                f"Yeni: {result.get('pages_ingested')} sayfa\n"
                f"Toplam: {result.get('total_knowledge_pages')}"
            )

        # --- Finance ---
        if any(k in lower for k in ["hisse", "borsa", "kripto", "bitcoin", "btc", "ethereum", "piyasa", "finans", "stock", "crypto", "fiyat"]):
            if hasattr(self.pipeline, "finance"):
                return self.pipeline.finance.analyze(message)

        # --- Image generation ---
        if any(k in lower for k in ["görsel üret", "resim çiz", "image generate", "görüntü oluştur", "çiz:", "generate image"]):
            prompt = message
            for prefix in ["görsel üret", "resim çiz", "image generate", "görüntü oluştur", "çiz:", "generate image"]:
                if prefix in lower:
                    prompt = message[lower.find(prefix) + len(prefix):].strip(" :")
                    break
            if hasattr(self.pipeline, "image_gen"):
                result = self.pipeline.image_gen.generate(prompt or message)
                if result.get("success"):
                    return f"🖼️ Görsel oluşturuldu ({result.get('source')})\nDosya: {result.get('filename')}\nPrompt: {result.get('prompt')}"
                return f"Görsel üretilemedi: {result.get('error')}"

        # --- GitHub ---
        if any(k in lower for k in ["github", "repolarım", "repo listele", "pr aç", "issue aç"]):
            if hasattr(self.pipeline, "github") and self.pipeline.github.enabled:
                if "listele" in lower or "repolar" in lower:
                    repos = self.pipeline.github.list_repos(15)
                    if not repos:
                        return "Repo bulunamadı veya token yok."
                    lines = ["📦 GitHub Repoların:"]
                    for r in repos:
                        priv = "🔒" if r["private"] else "🌐"
                        lines.append(f"{priv} {r['full_name']} ({r.get('language') or '?'})")
                    return "\n".join(lines)
                return "GitHub hazır. Örnek: 'repolarımı listele' veya dosya yazma için onaylı komut kullan."
            return "GitHub token ayarlı değil. .env içine GITHUB_TOKEN ekle."

        # --- Status ---
        if lower in ("/status", "durum", "status", "ne durumda"):
            return self.get_status()

        return None  # no tool matched → fall to LLM

    def chat(self, user_message: str) -> str:
        user_message = user_message.strip()
        if not user_message:
            return "Mesaj boş."

        # 1) Aggressive tool routing first
        tool_reply = self._try_tools(user_message)
        if tool_reply is not None:
            self.memory.extract_and_learn(user_message, tool_reply)
            return tool_reply

        # 2) LLM with full context + available tools description
        context = self.memory.get_context_for_prompt(user_message)
        tools_hint = ""
        if self.pipeline:
            tools_hint = """
Kullanabileceğin araçlar (kullanıcı isterse öner veya kullan):
- Website tarama, debug, kod düzeltme
- Bilgi evreni genişletme
- Finans / kripto analizi
- Görsel üretimi
- GitHub işlemleri (izinli)
"""

        prompt = f"""{SYSTEM_PROMPT}

### Kullanıcı Profili & Hafıza
{context}
{tools_hint}

### Kullanıcı
{user_message}

Kısa ve yararlı cevap ver. Gerekirse araç önermeyi unutma."""

        try:
            reply = self.ollama.chat(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ]
            )
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            reply = f"Model şu an cevap veremedi: {e}"

        self.memory.extract_and_learn(user_message, reply)
        return reply

    def get_status(self) -> str:
        p = self.memory.profile
        name = p.get("name") or "Henüz isim yok"
        facts = len(p.get("facts", []))
        projects = ", ".join(p.get("projects", [])[-3:]) or "-"
        extra = ""
        if self.pipeline:
            uni = getattr(self.pipeline, "expander", None)
            if uni:
                st = uni.get_status()
                extra = f"\n🌌 Bilgi: {st.get('total_pages', 0)} parça | Tur: {st.get('total_runs', 0)}"
            gh = getattr(self.pipeline, "github", None)
            if gh and gh.enabled:
                extra += "\n🐙 GitHub: bağlı"
        return (
            f"🧠 Sentinel Hazır\n"
            f"Sahip: {name}\n"
            f"Bilinen gerçek: {facts}\n"
            f"Projeler: {projects}\n"
            f"İzin modeli: aktif"
            f"{extra}"
        )
