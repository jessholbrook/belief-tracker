#!/usr/bin/env bash
# First-time project setup: Python venv, deps, frontend deps, .env.
set -euo pipefail

cd "$(dirname "$0")"

# Pick a Python ≥ 3.10 — the backend uses modern union syntax, and on macOS
# the bare `python3` is often the ancient system 3.9.
PYTHON=""
for p in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$p" >/dev/null 2>&1 &&
     "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    PYTHON="$p"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  echo "Error: Python 3.10+ is required (found $(python3 --version 2>&1))." >&2
  exit 1
fi

echo "→ Setting up backend (using $PYTHON)"
cd backend
if [ ! -d venv ]; then
  "$PYTHON" -m venv venv
fi
# shellcheck source=/dev/null
source venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt -r requirements-dev.txt
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
