#!/usr/bin/env bash
set -euo pipefail

model=${VLLM_MODEL:-Qwen/Qwen2.5-1.5B-Instruct}
python -m vllm.entrypoints.openai.api_server --model "$model" --host 0.0.0.0 --port 8000
