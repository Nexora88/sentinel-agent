"""
SEKA Personal Assistant — agresif tool-calling, Türkçe, yerel.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from core.ollama_client import OllamaClient
from core.personal_memory import PersonalMemory
from core.permission_manager import PermissionManager, Action

logger = logging.getLogger("seka.assistant")

SYSTEM_PROMPT = """Sen SEKA'sın — Sentinel Egemen Kişisel Ajan.
Kullanıcının yerel, sürekli gelişen AI'sısın (Ollama). Model çıkarımı cihaz üzerinde kalır. Harici ağ özellikleri kapalı varsayılır; entegrasyon açılmadıkça kişisel veriyi dış servislere gönderme. Mutlak gizlilik garantisi verme.

Yetkinlikler:
- Kod inceleme, debug, güvenlik, dosya düzeltme (onaylı yazma)
- GitHub (izinli push/PR)
- Paper finans (sanal), piyasa analizi
- Bilgi evreni, merak, gece araştırması, podcast taslağı
- Plan motoru (çok adımlı), bilgi paketi dışa aktarımı
- Website savunma taraması, görsel üretimi

Türkçe ve etik gelişim:
- Her zaman doğal, doğru yazımlı, anlaşılır Türkiye Türkçesi kullan; gereksiz İngilizce terimleri açık Türkçe karşılığıyla anlat.
- Kullanıcının dil düzeltmelerinden ve onaylı yerel bilgi notlarından öğren; yeni kelime/iddiaları doğrulanmış gerçek gibi sunma.
- Belirsizliği dürüstçe belirt, kaynak ile çıkarımı ayır, bilmediğini uydurma; kişisel veriyi gereksiz tekrar etme.
- Saygılı, adil, şiddeti ve zararı azaltan, ayrımcılıktan uzak bir dil kullan; hatayı savunmak yerine düzelt ve nedenini açıkla.
- Öğrenme, model ağırlıklarının kendi kendine eğitildiği anlamına gelmez; kalıcı gelişim yerel ve denetlenebilir bellek/kurallar üzerinden olur.

Kurallar:
- Yazma/push/PR otomatik değil
- Yerel model uç noktası dışına AI isteği gönderme; uzaktaki LLM/API kullanma
- Web araştırması ve bildirim entegrasyonları açıkça etkinleştirilmedikçe dış ağa veri gönderme
- Gerçek para / yıkıcı shell yok
- Kısa, net, eylem odaklı Türkçe
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
        if not self.pipeline:
            return None

        lower = message.lower().strip()

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

        # Plan
        if lower.startswith("planla:") or lower.startswith("plan:"):
            goal = message.split(":", 1)[-1].strip()
            plan = self.pipeline.create_plan(goal)
            if not plan.get("success") and plan.get("error"):
                return plan["error"]
            lines = [f"🗺 Plan: {plan.get('goal')} (id {plan.get('id')})"]
            for i, s in enumerate(plan.get("steps") or [], 1):
                lock = "🔒" if s.get("needs_approval") else "⚡"
                lines.append(f"{i}. {lock} {s.get('title')} [{s.get('type')}]")
            lines.append("Güvenli adımlar için Web → Plan Motoru → Çalıştır.")
            return "\n".join(lines)

        if any(k in lower for k in ["bilgi paketi", "paket dışa", "knowledge pack", "paket üret"]):
            r = self.pipeline.export_knowledge_pack()
            if r.get("success"):
                return f"📦 Paket hazır\nJSON: {r.get('json_path')}\nMD: {r.get('md_path')}"
            return "Paket üretilemedi."

        if any(k in lower for k in ["merak turu", "merak et", "curiosity"]):
            r = self.pipeline.run_curiosity()
            return f"🔭 Merak: {r.get('topic')}\n{str(r.get('reflection', ''))[:800]}"

        if any(k in lower for k in ["site tara", "website tara", "güvenlik tara", "scan site"]):
            url_m = re.search(r"https?://[^\s]+", message)
            if url_m:
                return self.pipeline.scan_website(url_m.group(0))

        if any(k in lower for k in ["debug", "hata ayıkla", "şu hatayı", "error:"]):
            return self.pipeline.debug_error(message)

        if any(k in lower for k in ["genişlet", "öğren internet", "bilgi evreni", "expand knowledge"]):
            topic = None
            m = re.search(r"(?:konu|topic)[:= ]+(.+)", message, re.I)
            if m:
                topic = m.group(1).strip()
            result = self.pipeline.expand_knowledge(topic=topic)
            return (
                f"🌌 Bilgi evreni\nKonu: {result.get('topic')}\n"
                f"Yeni: {result.get('pages_ingested')} · Toplam: {result.get('total_knowledge_pages')}"
            )

        if any(k in lower for k in ["hisse", "borsa", "kripto", "bitcoin", "btc", "ethereum", "piyasa", "finans", "crypto"]):
            if hasattr(self.pipeline, "finance"):
                return self.pipeline.finance.analyze(message)

        if any(k in lower for k in ["görsel üret", "resim çiz", "image generate", "çiz:"]):
            prompt = message
            for prefix in ["görsel üret", "resim çiz", "image generate", "çiz:"]:
                if prefix in lower:
                    prompt = message[lower.find(prefix) + len(prefix):].strip(" :")
                    break
            if hasattr(self.pipeline, "image_gen"):
                result = self.pipeline.image_gen.generate(prompt or message)
                if result.get("success"):
                    return f"🖼️ {result.get('filename')} ({result.get('source')})"
                return f"Görsel hata: {result.get('error')}"

        if any(k in lower for k in ["github", "repolarım", "repo listele"]):
            if hasattr(self.pipeline, "github") and self.pipeline.github.enabled:
                if "listele" in lower or "repolar" in lower:
                    repos = self.pipeline.github.list_repos(15)
                    lines = ["📦 GitHub:"] + [
                        f"{'🔒' if r['private'] else '🌐'} {r['full_name']}" for r in repos
                    ]
                    return "\n".join(lines) if repos else "Repo yok."
                return "GitHub hazır. Örn: repolarımı listele"
            return "GITHUB_TOKEN yok."

        if lower in ("/status", "durum", "status", "ne durumda"):
            return self.get_status()

        return None

    def chat(self, user_message: str) -> str:
        user_message = user_message.strip()
        if not user_message:
            return "Mesaj boş."

        tool_reply = self._try_tools(user_message)
        if tool_reply is not None:
            self.memory.extract_and_learn(user_message, tool_reply)
            return tool_reply

        context = self.memory.get_context_for_prompt(user_message)
        prompt = f"""{SYSTEM_PROMPT}

### Profil & Hafıza
{context}

### Kullanıcı
{user_message}

Kısa ve yararlı cevap. Gerekirse planla: / paket / genişlet öner."""

        try:
            reply = self.ollama.chat(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ]
            )
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            reply = f"Model cevap veremedi: {e}"

        self.memory.extract_and_learn(user_message, reply)
        return reply

    def get_status(self) -> str:
        p = self.memory.profile
        name = p.get("name") or "İsimsiz sahip"
        facts = len(p.get("facts", []))
        projects = ", ".join(p.get("projects", [])[-3:]) or "-"
        extra = ""
        if self.pipeline:
            uni = getattr(self.pipeline, "expander", None)
            if uni:
                st = uni.get_status()
                extra = f"\n🌌 Bilgi: {st.get('total_pages', 0)}"
            gh = getattr(self.pipeline, "github", None)
            if gh and gh.enabled:
                extra += "\n🐙 GitHub: bağlı"
        return (
            f"◈ SEKA Hazır\n"
            f"Sahip: {name}\n"
            f"Gerçek: {facts} · Projeler: {projects}\n"
            f"İzin modeli: aktif{extra}"
        )
