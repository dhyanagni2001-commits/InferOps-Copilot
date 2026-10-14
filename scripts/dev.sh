#!/usr/bin/env bash
set -euo pipefail

# Always use the project environment instead of requiring global Python tools.
if [[ ! -x .venv/bin/uvicorn ]]; then
  echo "Missing backend dependencies. Run: .venv/bin/pip install -e './backend[dev]'"
  exit 1
fi

# Port 8081 avoids common IDE forwarding conflicts on port 8080.
.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8081 --reload &
api_pid=$!
npm --prefix frontend run dev &
ui_pid=$!

# Stop only the two child servers when Ctrl-C is pressed.
cleanup() { kill "$api_pid" "$ui_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
wait
