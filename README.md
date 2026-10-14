# Sentinel Agent v3

Self-hosted, continuously expanding multi-agent system powered by **Ollama**.  
No paid APIs required. Fully under your control.

## Yeni Yetenekler (v3)

| Motor | Açıklama |
|-------|----------|
| **Web Arayüzü** | Telefon + PC tarayıcı, sesli komut (🎤) |
| **Bilgi Evreni** | İnternetten yavaş yavaş öğrenir, sürekli büyür |
| **GitHub** | Repo listele, dosya yaz, commit/push, issue/PR (izinli) |
| **Finans** | Hisse (yfinance) + kripto (CoinGecko) + LLM analizi |
| **Görsel** | Local Stable Diffusion veya ücretsiz Pollinations |
| **Multi-user** | Owner / admin / user rolleri, token auth |
| **Agresif tool-calling** | Doğal dil → otomatik araç seçimi |
| **Cloud-ready** | Docker + persistent volume (bilgi diskte büyür) |

## Hızlı Başlangıç

```bash
pip install -r requirements.txt
cp .env.example .env
# GITHUB_TOKEN ve diğerlerini düzenle

python -m scripts.run web
# → http://localhost:8000
```

### Docker / Cloud

```bash
docker compose up -d --build
```

`sentinel_memory` volume'u bilgi evreninin diskte büyümesini sağlar (bulut VPS'te yer kaplar).

## Komutlar

```bash
python -m scripts.run web              # Ana arayüz
python -m scripts.run chat             # Terminal sohbet
python -m scripts.run expand           # Bilgi evrenini büyüt
python -m scripts.run expand --topic "rust async"
python -m scripts.run schedule         # Gece review + 90dk'da bir genişleme
python -m scripts.run repo <url>
python -m scripts.run debug "error..."
python -m scripts.run website https://...
python -m scripts.run fix file.py "issue"
```

## Web Arayüzü Panelleri

- **Sohbet** + 🎤 sesli komut (tarayıcı SpeechRecognition)
- **Bilgi Evreni** — tohum ekle, genişlet, istatistik
- **Finans** — "Bitcoin fiyatı", "AAPL analizi", "piyasa özeti"
- **Görsel** — prompt yaz, üret
- **GitHub** — repolarını gör
- **Onaylar** — yazma/push isteklerini onayla/reddet
- **Durum**

## GitHub Kurulumu

1. GitHub → Settings → Developer settings → Personal access tokens
2. `repo` scope'lu token oluştur
3. `.env` içine `GITHUB_TOKEN=ghp_...` yaz

Artık sohbette "repolarımı listele" diyebilir, onaylı yazma/push yapabilirsin.

## İzin Modeli

- Okuma / analiz → serbest
- Dosya yazma, commit, push, PR → **senin açık onayın şart**
- Multi-user: sadece owner/admin onaylayabilir

## Ortam Değişkenleri

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:32b
GITHUB_TOKEN=
OWNER_PASSWORD=sentinel-change-me
AUTH_REQUIRED=false
SD_API_URL=          # opsiyonel local Automatic1111
WHATSAPP_PHONE=
WHATSAPP_APIKEY=
```

## Mimari

```
Web UI / CLI
    ↓
PersonalAssistant (agresif tool routing)
    ├── Code Reviewer / Debugger / Security
    ├── Knowledge Expander (sürekli büyüyen evren)
    ├── GitHub Client (izinli yazma/push)
    ├── Finance Engine
    ├── Image Generator
    └── Personal Memory + RAG
```

Her şey local. Bilgi evreni ve hafıza diskte kalıcı olarak büyür.

## Lisans

MIT
