#!/usr/bin/env bash
# First-time project setup: Python venv, deps, frontend deps, .env.
set -euo pipefail

cd "$(dirname "$0")"

echo "→ Setting up backend"
cd backend
if [ ! -d venv ]; then
  python3 -m venv venv
fi
# shellcheck source=/dev/null
source venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  Created backend/.env — add your ANTHROPIC_API_KEY"
fi
deactivate
cd ..

echo "→ Setting up frontend"
cd frontend
npm install
cd ..

echo
echo "Setup complete."
echo "  1. Edit backend/.env and set ANTHROPIC_API_KEY"
echo "  2. Run ./start.sh"
