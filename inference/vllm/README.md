# vLLM

`serve.sh` starts an OpenAI-compatible server for the pinned instruction model. In a GPU environment with vLLM installed:

```bash
./inference/vllm/serve.sh
USE_LLM=true VLLM_BASE_URL=http://127.0.0.1:8000/v1 make dev
```

The backend sends a `json_schema` `response_format`, so vLLM constrains decoding to `{summary, evidence_ids, suggested_actions}`. Output is still validated: cited IDs must exist among the collected evidence. On any failure the rule-based diagnosis is returned with a limitation, and `inferops_dependency_failures_total{dependency="llm"}` is incremented.

Not yet validated on GPU hardware; see `docs/gpu-deployment.md`.
