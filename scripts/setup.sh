#!/bin/bash
set -e

echo "Setting up Sentinel Agent..."

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy env file if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file — please edit it."
fi

echo "Setup complete."
echo "Next: edit .env and run 'docker compose up -d' or 'python -m scripts.run'"
