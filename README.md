# Sentinel Agent v3.2

Self-hosted, continuously expanding multi-agent system powered by **Ollama**.  
No paid APIs required. Fully under your control. Strict permission model.

## Prerequisites

1. **Python 3.12+**
2. **Ollama** running (`ollama serve`)
3. Models:

```bash
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text
```

```env
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_EMBED_MODEL=nomic-embed-text
```

## Quick start

```bash
git clone https://github.com/Nexora88/sentinel-agent.git
cd sentinel-agent
pip install -r requirements.txt
cp .env.example .env
python -m scripts.run test
python -m scripts.run web
```

Docker:

```bash
docker compose up -d --build
```

## What is implemented (safe)

| Module | Behavior |
|--------|----------|
| Knowledge Universe | Slow web ingest + credibility heuristics |
| Curiosity Matrix | Idle topic exploration (science, philosophy, CS) |
| Night Research | Proposals only |
| Paper Finance | Virtual portfolio only |
| License checker | Local copyright/license hygiene |
| Document assistant | Dates/amounts → **suggestions**, no payments |
| Local discovery | Localhost ports, **read-only** |
| Energy policy | Prefer off-peak hours for heavy jobs |
| Legacy backup | Encrypted **local** snapshot (not blockchain) |
| GitHub / code | Write & push only with approval |

## Explicit non-goals (not implemented)

These were requested as “AI organization” features but are **intentionally out of scope**:

- Autonomous company formation (LLC / e-Residency / Stripe Atlas)
- Autonomous freelancing contracts (Upwork/Fiverr sign & negotiate)
- Real-money NFT sales or real trading
- IoT / camera **control** (only optional read-only localhost report)
- Open P2P swarm, mesh VPN, or global signature distribution
- Auto-pay bills from OCR
- Medical diagnosis (research reading only; not advice)

## Commands

```bash
python -m scripts.run web
python -m scripts.run expand
python -m scripts.run curiosity
python -m scripts.run night
python -m scripts.run finance          # paper only
python -m scripts.run licenses
python -m scripts.run discover         # localhost ports
python -m scripts.run doc-analyze f.txt
python -m scripts.run legacy-backup --passphrase 'your-long-secret'
python -m scripts.run schedule
python -m scripts.run secrets
python -m scripts.run ingest file.pdf
```

## Energy policy

```env
OFF_PEAK_START_HOUR=0
OFF_PEAK_END_HOUR=7
STRICT_ENERGY=false    # true => defer heavy jobs outside off-peak
FORCE_HEAVY_JOBS=false
```

## Security

- Prompt injection filter on scraped content
- Source credibility heuristic (arxiv/gov/edu preferred)
- Command / action whitelist
- Scheduler: timeout, max_instances=1, exception isolation
- Secrets only from `.env`

## License

MIT — see `LICENSE`
