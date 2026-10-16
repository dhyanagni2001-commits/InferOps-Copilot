# GPU deployment

`deploy/kubernetes/overlays/gpu` adds vLLM (one GPU), Triton (CPU instance group), and an ingestion Job, and switches the backend to `USE_LLM=true`, `EMBEDDING_BACKEND=triton`, and `USE_QDRANT=true`.

> Status: the overlay renders with `kubectl kustomize` and uses verified image tags and model revisions, but it has not been applied to a GPU cluster. The Triton and Qdrant parts were validated in Docker (see the technical report).

## Prerequisites

1. NVIDIA GPU Operator or device plugin; confirm with `kubectl get nodes -o jsonpath='{.items[*].status.allocatable.nvidia\.com/gpu}'`.
2. A default StorageClass (Qdrant data and the vLLM Hugging Face cache use PVCs).
3. Images pushed to your registry; edit the `images:` block in the overlay:
   ```bash
   docker build -f deploy/docker/backend.Dockerfile -t REGISTRY/inferops/backend:0.2.0 .
   docker build -f deploy/docker/frontend.Dockerfile -t REGISTRY/inferops/frontend:0.2.0 .
   python inference/triton/export_embedding_model.py   # then:
   docker build -f deploy/docker/model-repository.Dockerfile -t REGISTRY/inferops/model-repository:minilm .
   ```
4. Secret: `kubectl create secret generic inferops-secrets -n inferops-demo --from-literal=API_BEARER_TOKEN="$(openssl rand -hex 24)"`. Add `HF_TOKEN` for gated models.

## Deploy and verify

```bash
./scripts/deploy.sh gpu
kubectl wait -n inferops-demo --for=condition=complete job/inferops-ingest --timeout=10m
kubectl port-forward -n inferops-demo svc/inferops-frontend 8080:80
curl -s localhost:8080/health/ready     # expect checks.vllm and checks.triton true
```

Then run `make eval BASE_URL=http://127.0.0.1:8080 TOKEN=...`. Diagnoses should report `generated_by: llm`. Any `rules` result with an "instruction model was not used" limitation means the model output was rejected; the reason is in the backend logs (`llm_fallback`).

## Pinned versions

| Component | Version |
|---|---|
| vLLM image | `vllm/vllm-openai:v0.11.0` |
| Instruction model | `Qwen/Qwen2.5-1.5B-Instruct` @ `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, `--max-model-len 8192`, `--gpu-memory-utilization 0.85` |
| Triton image | `nvcr.io/nvidia/tritonserver:25.08-py3` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` @ `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`, 384-d, mean pooling + L2 norm in-graph, 256 tokens |
| Qdrant | `qdrant/qdrant:v1.15.5` |
| kubectl in backend image | v1.37.0, checksum-verified |

Record GPU model, driver, and measured memory in the technical report after the first deployment.
