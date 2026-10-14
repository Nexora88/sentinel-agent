# Sentinel Agent

Self-hosted multi-agent system powered by **Ollama**.  
No external paid APIs. Fully under your control.  
Kişisel, gizli, sürekli genişleyen bilgi evreni.

## Özellikler

- **Web Arayüzü** — Telefon + PC’den tarayıcı ile komut ver
- **Kişisel Hafıza** — Seni tanır, tercihlerini ve projelerini hatırlar
- **Bilgi Evreni** — İnternetten yavaş yavaş beslenir, sürekli büyür (uzay gibi)
- Kod inceleme (gece uykundayken)
- Defansif güvenlik taraması (kod + website)
- Hata ayıklama & izin kontrollü kod yazma / düzeltme
- WhatsApp bildirimleri (opsiyonel, CallMeBot)
- Strict permission modeli (yazma / push sadece senin onayınla)

## Hızlı Başlangıç

```bash
pip install -r requirements.txt

# Web arayüzünü başlat (önerilen)
python -m scripts.run web

# Tarayıcıda aç:
# http://localhost:8000
```

## Komutlar

```bash
# Web UI (ana arayüz)
python -m scripts.run web --port 8000

# Terminal sohbet
python -m scripts.run chat

# Bilgi evrenini bir kez genişlet
python -m scripts.run expand
python -m scripts.run expand --topic "rust async programming"

# Scheduler (gece inceleme + her ~90 dk bilgi genişlemesi)
python -m scripts.run schedule

# Diğer
python -m scripts.run review dosya.py
python -m scripts.run repo https://github.com/sen/proje.git
python -m scripts.run debug "TypeError: ..." --file app.py
python -m scripts.run website https://siten.com
python -m scripts.run fix app.py "null check ekle"
python -m scripts.run test
```

## Bilgi Evreni Nasıl Çalışır?

- DuckDuckGo ile ücretsiz arama yapar
- Sayfaları saygılı şekilde çeker (rate limit + robots dostu)
- Trafilatura + local LLM ile yüksek kaliteli özet üretir
- ChromaDB’ye yazar → RAG ile her soruda kullanılabilir hale gelir
- Scheduler ile her ~90 dakikada bir yavaş yavaş büyür
- İstediğin konuları tohum olarak ekleyebilirsin (web arayüzünden veya CLI)

Hiçbir veri dışarı çıkmaz. Her şey senin sunucunda / bilgisayarında kalır.

## Web Arayüzü

- **Sohbet**: Doğal dilde emir ver
- **Bilgi Evreni**: İstatistikler, tohum ekle, manuel genişlet
- **Onaylar**: Yazma / push isteklerini onayla veya reddet
- **Durum**: Sistem + evren özeti

## Permission Modeli

Varsayılan:
- Okuma & raporlama → serbest
- Dosya yazma, commit, push → **senin açık onayın şart**

## Ortam Değişkenleri (.env)

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:32b
OLLAMA_EMBED_MODEL=nomic-embed-text

REQUIRE_APPROVAL=true
WATCH_REPOS=

# Opsiyonel WhatsApp bildirim
WHATSAPP_PHONE=
WHATSAPP_APIKEY=

# Web
WEB_PORT=8000
```

## Mimari

- **Ollama** → tüm zeka local
- **CrewAI + özel ajanlar** → code reviewer, security, debugger, learner, personal assistant, knowledge expander
- **ChromaDB** → kod hafızası + kişisel hafıza + bilgi evreni
- **FastAPI** → self-hosted web kontrol paneli
- **APScheduler** → gece görevleri + sürekli genişleme

## Lisans

MIT
