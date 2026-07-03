#!/usr/bin/env bash
# Free ports 1337 and 5173.
set -euo pipefail

for port in 1337 5173; do
  pids=$(lsof -t -i ":${port}" 2>/dev/null || true)
  if [ -n "${pids}" ]; then
    echo "Killing PID(s) ${pids//$'\n'/ } on port ${port}"
    echo "${pids}" | xargs kill 2>/dev/null || true
  fi
done
