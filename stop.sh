#!/usr/bin/env bash
# Free ports 1337 and 5173.
set -euo pipefail

for port in 1337 5173; do
  pid=$(lsof -t -i ":${port}" 2>/dev/null || true)
  if [ -n "${pid}" ]; then
    echo "Killing PID ${pid} on port ${port}"
    kill "${pid}" 2>/dev/null || true
  fi
done
