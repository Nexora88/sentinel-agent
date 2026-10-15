# Contributing to Sentinel Agent

Thanks for your interest. This project is primarily personal / self-hosted, but improvements are welcome.

## How to contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-improvement`)
3. Make focused, well-tested changes
4. Follow existing code style (Python 3.12, type hints where practical)
5. Open a Pull Request with a clear description

## Rules

- **No offensive capabilities** — only defensive security features
- **Permission model must stay strict** — write / push / destructive actions always require human approval
- **No automatic spending of money**, no autonomous account creation, no bug-bounty bots
- Prefer local / free tools (Ollama, DuckDuckGo, etc.)
- Keep dependencies minimal

## Development setup

```bash
# Prerequisites
# - Python 3.12+
# - Ollama installed and running
# - Models pulled: ollama pull qwen2.5-coder:7b  (or 32b) and nomic-embed-text

pip install -r requirements.txt
cp .env.example .env
python -m scripts.run test
```

## Code of conduct

Be respectful. This is a security-sensitive personal agent — treat it carefully.


## Security and model-data expectations

- Never commit secrets, personal data, private customer code, proprietary weights or datasets without clear redistribution rights.
- Do not claim model provenance, national origin, benchmark superiority, certification or hardware support without reproducible evidence.
- Include source, license, revision/hash, collection date, filtering steps and known limitations for model/data contributions.
- Never ingest secrets or unauthorized personal/customer data. Keep training, validation and held-out test sets separate.

## Pull request checklist

- [ ] The change is scoped and includes regression tests.
- [ ] External network access is explicit, allowlisted and documented.
- [ ] File writes, tool use, code changes and deployment retain approval gates.
- [ ] Turkish and English documentation are updated where relevant.
- [ ] Untested hardware, deployment and security boundaries are stated.
- [ ] CI passes on the exact PR head.

If a test requires a model, accelerator, network or external service, document the setup and expected result. Never silently skip a failed security test.
