#!/usr/bin/env sh
# One-command MKAOS bootstrap. Does not download model weights.
set -eu

OFFLINE=0
if [ "${1:-}" = "--offline" ]; then
  OFFLINE=1
elif [ "$#" -gt 0 ]; then
  echo "Usage: $0 [--offline]" >&2
  exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Desktop/Engine, then retry." >&2
  exit 2
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required (docker compose)." >&2
  exit 2
fi

if [ ! -f .env ]; then
  if [ ! -f .env.example ]; then
    echo ".env.example is missing; refusing to invent configuration." >&2
    exit 2
  fi
  cp .env.example .env
  chmod 600 .env 2>/dev/null || true
  echo "Created .env from .env.example."
fi

# Create a strong owner secret once, persist it with private file permissions,
# and display it only to this interactive terminal. Never write it to app logs.
OWNER_SECRET="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
export OWNER_SECRET
python3 - <<'PY'
import os
from pathlib import Path
path = Path(".env")
lines = path.read_text(encoding="utf-8").splitlines()
found = False
for i, line in enumerate(lines):
    if line.startswith("OWNER_PASSWORD="):
        found = True
        if not line.partition("=")[2].strip():
            lines[i] = "OWNER_PASSWORD=" + os.environ["OWNER_SECRET"]
        break
if not found:
    lines.append("OWNER_PASSWORD=" + os.environ["OWNER_SECRET"])
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
try:
    path.chmod(0o600)
except OSError:
    pass
PY

if grep -q '^OWNER_PASSWORD=$' .env; then
  echo "OWNER_PASSWORD could not be initialized; inspect .env locally." >&2
  exit 2
fi

echo "Starting MKAOS web service..."
if [ "$OFFLINE" -eq 1 ]; then
  echo "Offline mode: no image build or model download will be attempted."
  docker compose up -d --no-build
else
  echo "Build mode may need internet for OS/Python/Rust dependencies; model weights are never downloaded."
  docker compose up -d --build
fi

echo
echo "MKAOS web UI: http://localhost:${WEB_PORT:-8000}"
echo "Readiness endpoint: http://localhost:${WEB_PORT:-8000}/api/model/readiness"
echo "If no reviewed native checkpoint exists, chat will show a setup-required message, not pretend to generate AI."
echo "Set OWNER_PASSWORD yourself in .env before sharing or exposing this installation."
