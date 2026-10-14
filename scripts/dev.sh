#!/usr/bin/env bash
set -euo pipefail

# Run the API and UI together; Ctrl-C stops both processes.
trap 'kill 0' EXIT
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8080 --reload &
npm --prefix frontend run dev &
wait
