#!/usr/bin/env bash
set -euo pipefail

model=${VLLM_MODEL:-Qwen/Qwen2.5-1.5B-Instruct}
revision=${VLLM_REVISION:-989aa7980e4cf806f80c7fef2b1adb7bc71aa306}
exec python -m vllm.entrypoints.openai.api_server --model "$model" --revision "$revision" \
  --max-model-len "${VLLM_MAX_MODEL_LEN:-8192}" --gpu-memory-utilization "${VLLM_GPU_MEMORY_UTILIZATION:-0.85}" \
  --host 0.0.0.0 --port "${VLLM_PORT:-8000}"
