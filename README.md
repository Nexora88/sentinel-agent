# Sentinel Agent v3.1

Self-hosted, continuously expanding multi-agent system powered by **Ollama**.  
No paid APIs required. Fully under your control. Strict permission model.

## Prerequisites (Ön Gereksinimler)

Sistemin çalışması için şunlar **zorunlu**:

1. **Python 3.12+**
2. **Ollama** kurulu ve çalışıyor olmalı  
   - Kurulum: https://ollama.com  
   - Servisi başlat: `ollama serve`
3. **Modelleri önceden çek**:

```bash
# Önerilen (daha hızlı, tüketici GPU / CPU için)
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text

# Daha güçlü (en az 24GB VRAM önerilir)
ollama pull qwen2.5-coder:32b
ollama pull nomic-embed-text
```

`.env` içinde hangi modeli kullanacağını belirt:

```env
OLLAMA_MODEL=qwen2.5-coder:7b          # veya 32b
OLLAMA_EMBED_MODEL=nomic-embed-text
```

> 32b model çok güçlüdür ama yavaş olabilir. Başlangıç için **7b** önerilir.

## Hızlı Başlangıç

### Yerel (pip)

```bash
git clone https://github.com/Nexora88/sentinel-agent.git
cd sentinel-agent
pip install -r requirements.txt
cp .env.example .env
# .env dosyasını düzenle (GITHUB_TOKEN vb.)

python -m scripts.run test
python -m scripts.run web
# → http://localhost:8000
```

### Docker (önerilen — bulut / VPS)

```bash
cp .env.example .env
# .env düzenle

docker compose up -d --build
```

- Web UI: `http://localhost:8000`
- Hafıza ve bilgi evreni `sentinel_memory` volume’unda kalıcıdır (container silinse bile kaybolmaz).
- Ollama host’ta çalışıyorsa `OLLAMA_BASE_URL=http://host.docker.internal:11434` kullanılır.

## Ana Özellikler

| Özellik | Açıklama |
|---------|----------|
| Web Arayüzü | Sohbet, sesli komut (🎤), paneller |
| Bilgi Evreni | İnternetten yavaş öğrenme + **yerel PDF/MD yükleme** |
| GitHub | Repo listele, dosya yaz, push, PR (**izinli**) |
| Finans | Hisse + kripto analizi |
| Görsel | Local SD veya ücretsiz Pollinations |
| Secret Scanning | Hardcoded API key / şifre tespiti |
| Night Research | Gece güvenli araştırma + öneri raporu |
| Multi-user | Owner / admin / user rolleri |
| Strict Permissions | Yazma / push asla otomatik değil |

## Güvenlik (Kritik)

- **Prompt Injection koruması**: Scraped web içeriği `core/safety.py` ile temizlenir.
- **Komut whitelist**: Sadece tanımlı aksiyonlar önerilebilir.
- **Yazma / push / PR**: Her zaman insan onayı gerekir.
- **Gece modu**: Sadece bilgi toplar + rapor yazar. Para harcamaz, sunucu kiralamaz, otomatik push yapmaz.
- Secret scanner commit öncesi uyarı verir.

## Komutlar

```bash
python -m scripts.run web                 # Web UI
python -m scripts.run chat                # Terminal sohbet
python -m scripts.run expand              # Bilgi evrenini büyüt
python -m scripts.run expand --topic "..."
python -m scripts.run secrets             # Gizli anahtar tara
python -m scripts.run ingest dosya.pdf    # Yerel belgeyi RAG’e ekle
python -m scripts.run night               # Bir gece araştırma döngüsü
python -m scripts.run schedule            # Otomatik zamanlayıcı
python -m scripts.run repo <url>
python -m scripts.run debug "error..."
python -m scripts.run website https://...
python -m scripts.run fix file.py "issue"
python -m scripts.run test
```

## Night Research (Güvenli Gece Modu)

```bash
python -m scripts.run night
# veya schedule içinde her gece ~03:30
```

Ne yapar:
- Bilgi evrenini biraz genişletir
- Projede secret tarar
- İyileştirme **önerileri** üretir
- Raporu `memory/night_reports/` altına yazar
- WhatsApp’a özet gönderebilir

Ne **yapmaz**:
- Para harcamaz / kripto cüzdan açmaz
- Bulut sunucu kiralamaz
- Otomatik commit / push yapmaz
- Bug bounty veya freelance iş almaz

## Model Önerileri

| Donanım | Önerilen model |
|---------|----------------|
| CPU / düşük VRAM | `qwen2.5-coder:7b` veya `llama3.1:8b` |
| 12–16 GB VRAM | `qwen2.5-coder:14b` |
| 24 GB+ VRAM | `qwen2.5-coder:32b` |

Embedding her zaman: `nomic-embed-text`

## Ortam Değişkenleri

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_EMBED_MODEL=nomic-embed-text
REQUIRE_APPROVAL=true
GITHUB_TOKEN=
OWNER_PASSWORD=sentinel-change-me
AUTH_REQUIRED=false
WHATSAPP_PHONE=
WHATSAPP_APIKEY=
SD_API_URL=          # opsiyonel local Automatic1111
```

## Mimari

```
Web UI / CLI / Scheduler
        ↓
PersonalAssistant (tool routing + memory)
        ├── Code / Security / Debugger
        ├── Knowledge Expander (sanitized)
        ├── Night Researcher (proposals only)
        ├── Secret Scanner
        ├── Document Ingester (PDF/MD)
        ├── GitHub Client (approval gated)
        ├── Finance + Image
        └── Safety layer (injection + whitelist)
```

## Katkı

`CONTRIBUTING.md` dosyasına bak. PR’lar kabul edilir; yıkıcı / otonom finans özellikleri kabul edilmez.

## Lisans

MIT — bkz. `LICENSE`
