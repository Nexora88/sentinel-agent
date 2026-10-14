# Sentinel Agent

**Self-hosted multi-agent system** powered by Ollama.  
No external paid APIs. Fully under your control.

## What it does

- Reviews your code for bugs and improvements while you sleep
- Performs **defensive** security analysis (finds issues, never exploits)
- Continuously learns from your codebase via RAG memory
- Only performs write actions when you explicitly allow it
- Cloud-ready (RunPod, Vast.ai, any VPS with GPU)

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Nexora88/sentinel-agent.git
cd sentinel-agent

# 2. Setup
cp .env.example .env
# edit .env → set your model and WATCH_REPOS

# 3. Install
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Make sure Ollama is running and model is pulled
ollama pull qwen2.5-coder:32b
ollama pull nomic-embed-text

# 5. Test
python -m scripts.run test

# Review a local file
python -m scripts.run review path/to/file.py

# Full pipeline on a repository
python -m scripts.run repo https://github.com/your/repo.git

# Start nightly scheduler
python -m scripts.run schedule
```

## Architecture

```
config/          → settings, agent roles, permissions
core/            → ollama, rag, pipeline, scheduler, permissions
agents/          → code_reviewer, security_scanner, learner, reporter
tools/           → git tools
scripts/         → CLI entrypoint
```

## Permission Model

By default everything that writes (commit, PR, modify files) requires your approval.  
Agents can freely read code and generate reports.

## License

MIT
