# SEKA v5 — Sentinel Egemen Kişisel Ajan

**Yerel süper ajan.** Ücretli API yok. Veri sende kalır. Türkçe komut merkezi.

Sıradan chatbot değil:

| Devrim katmanı | Ne işe yarar |
|----------------|--------------|
| **Canlı iş kuyruğu (SSE)** | Genişlet / gece / plan ilerlemesini anlık gör |
| **Plan motoru** | `planla: hedef` → çok adım, riskli olanlar onay ister |
| **Bilgi paketi** | Paylaşılabilir sanitize JSON/MD (kişisel veri yok) |
| **Model router** | Hızlı sohbet / derin analiz (Ollama) |
| **Bilgi evreni** | Güven skoru + injection filtresi ile büyür |
| **Paper finans** | Sanal portföy, kilitli risk |
| **Merak + gece + podcast taslağı** | Otonom araştırma, otomatik yayın yok |
| **İzin modeli** | Push/yazma asla sessizce olmaz |

## Kurulum

```bash
ollama serve
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text

git clone https://github.com/Nexora88/sentinel-agent.git
cd sentinel-agent
pip install -r requirements.txt
cp .env.example .env
python -m scripts.run web
# http://localhost:8000
```

Docker: `docker compose up -d --build`

## Hızlı komutlar

```bash
python -m scripts.run web
python -m scripts.run expand
python -m scripts.run curiosity
python -m scripts.run night && python -m scripts.run podcast
python -m scripts.run finance
python -m scripts.run schedule
```

Web’de: **Nabız** paneli (manifesto + canlı işler), **Plan Motoru**, köprü kartları.

## Bilinçli sınırlar

Otonom şirket, gerçek trading, açık P2P sürü, IoT kontrolü **yok** — bilinçli.

## Lisans

MIT
