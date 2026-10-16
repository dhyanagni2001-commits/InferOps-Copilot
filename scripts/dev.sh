#!/usr/bin/env bash
# Run the API (port 8081) and the Vite UI (port 5173) for local development.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -x .venv/bin/uvicorn ]]; then
  echo "Missing backend dependencies. Run: make install"
  exit 1
fi
[[ -f data/docs-index.json ]] || .venv/bin/python -m ingestion.build_index

.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8081 --reload --reload-dir backend &
api_pid=$!
npm --prefix frontend run dev &
ui_pid=$!

# Stop only the two child servers when Ctrl-C is pressed.
cleanup() { kill "$api_pid" "$ui_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
wait
