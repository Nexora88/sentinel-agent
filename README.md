# Sentinel Agent

Self-hosted, multi-agent AI system powered by **Ollama** (no external paid APIs).

## Core Purpose
- Continuously reviews your code for errors and improvements while you sleep
- Performs **defensive** security scans (finds vulnerabilities, never exploits)
- Learns from your codebase and documentation via RAG
- Only takes actions (commit, fix, open PR) when you explicitly give permission
- Fully cloud-ready (RunPod, Vast.ai, VPS, etc.)

## Architecture

```
sentinel-agent/
├── config/           # All settings & agent definitions
├── agents/           # Individual agents (reviewer, security, learner, reporter)
├── core/             # Ollama client, RAG, scheduler, permission system
├── tools/            # Git, code analysis, defensive security tools
├── memory/           # Vector store for continuous learning
├── scripts/          # Setup and run scripts
└── docker-compose.yml
```

## Tech Stack
- **Models**: Ollama (Qwen2.5-Coder, Llama 3.1, DeepSeek-Coder, etc.)
- **Agent Framework**: CrewAI (easy multi-agent orchestration)
- **Memory / Learning**: ChromaDB + RAG
- **Security Tools**: Bandit, Semgrep, Trivy (defensive only)
- **Scheduler**: APScheduler or cron

## Quick Start (Cloud)
1. Rent a GPU instance (RunPod / Vast.ai recommended)
2. Clone this repo
3. `cp .env.example .env` and edit
4. `docker compose up -d`
5. Agents start reviewing on schedule

## Permission Model
Agents can only **report** by default.  
Any write action (fix code, commit, open PR) requires explicit approval.

---
Built for autonomy with control.
