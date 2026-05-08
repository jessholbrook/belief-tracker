#!/usr/bin/env bash
# Start backend (port 1337) and frontend (port 5173) in dev mode.
set -euo pipefail

cd "$(dirname "$0")"

cleanup() {
  echo
  echo "Stopping..."
  jobs -p | xargs -r kill 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "→ Starting backend on http://localhost:1337"
(
  cd backend
  # shellcheck source=/dev/null
  source venv/bin/activate
  exec uvicorn app.main:app --reload --port 1337
) &

echo "→ Starting frontend on http://localhost:5173"
(
  cd frontend
  exec npm run dev
) &

wait
