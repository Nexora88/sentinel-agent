# SEKA v4 — Sentinel Egemen Kişisel Ajan

Yerel · Türkçe · **Ollama** · ücretli API yok  
Basit sohbet botu değil: **komut köprüsü + operasyon panelleri**.

## Ön gereksinimler

```bash
ollama serve
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text
```

```bash
pip install -r requirements.txt
cp .env.example .env
python -m scripts.run web
# → http://localhost:8000
```

Docker: `docker compose up -d --build`

## Ne var?

| Panel / Modül | Ne yapar |
|---------------|----------|
| **Köprü** | Tek tık komutlar + sesli emir + sohbet |
| Bilgi Evreni | İnternetten yavaş öğrenme (sanitize + güven skoru) |
| Merak | Boşta bilim / felsefe / CS keşfi |
| Gece + Podcast | Gece raporu → **sadece metin taslağı** (otomatik yayın yok) |
| Belgeler | PDF/MD yükle → RAG + tarih/tutar önerisi (ödeme yok) |
| Finans | Paper trading (sanal) |
| Keşif | Localhost port (salt okuma) |
| Legacy | Şifreli yerel yedek |
| GitHub / Onaylar | Yazma her zaman insan onayı |

## Komutlar

```bash
python -m scripts.run web
python -m scripts.run expand
python -m scripts.run curiosity
python -m scripts.run night
python -m scripts.run podcast
python -m scripts.run finance
python -m scripts.run ingest fatura.pdf
python -m scripts.run discover
python -m scripts.run legacy-backup --passphrase 'gizli-uzun'
python -m scripts.run schedule
```

## Bilinçli sınırlar

- Gerçek para / NFT satışı / otonom şirket yok  
- IoT kamera kontrolü yok  
- Açık P2P sürü yok  
- Podcast sadece yerel taslak  

## Lisans

MIT
