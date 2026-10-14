# vLLM

Install vLLM in a GPU environment, pin the model revision required by your deployment, then run:

```bash
VLLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct ./inference/vllm/serve.sh
```

Enable generation in the backend with `USE_LLM=true`. If vLLM is unavailable, the workflow logs the error and returns its deterministic diagnosis.
