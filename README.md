# Sentinel Agent

Self-hosted multi-agent system powered by **Ollama**.  
No external paid APIs. Fully under your control.

## Features

- Code review while you sleep
- Defensive security scanning (code + website)
- Continuous learning (RAG)
- Debugging help
- Permission-controlled code writing & fixing
- WhatsApp notifications (free via CallMeBot)
- Git push / commit only with your approval

## Quick Commands

```bash
python -m scripts.run test

# Review a file
python -m scripts.run review myfile.py

# Full repo scan
python -m scripts.run repo https://github.com/you/project.git

# Debug an error
python -m scripts.run debug "TypeError: 'NoneType' object is not subscriptable" --file app.py

# Scan your website (defensive only)
python -m scripts.run website https://yoursite.com

# Propose a fix (will ask permission before writing)
python -m scripts.run fix app.py "Fix the null pointer when user is not logged in"

# Start nightly scheduler
python -m scripts.run schedule
```

## WhatsApp Setup (Free)

1. Add **+34 644 21 99 05** to your contacts
2. Send this message: `I allow callmebot to send me messages`
3. You will receive an API key
4. Put phone and apikey into `.env`

## Permission Model

By default:
- Reading & reporting → allowed
- Writing files, committing, pushing → **requires your approval**

## License

MIT
