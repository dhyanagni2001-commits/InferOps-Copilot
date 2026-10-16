# Local setup

Requirements: Python 3.10+, Node 22+. For the cluster and retrieval paths, also Docker, kind, and kubectl.

## Demo mode (no cluster)

```bash
make install
make dev            # API http://127.0.0.1:8081, UI http://localhost:5173, token: dev-token
make test test-ui   # backend tests and Playwright browser tests
```

## Against a real cluster from your machine

```bash
make index
DEMO_MODE=false K8S_ALLOWED_NAMESPACES=inferops-demo .venv/bin/uvicorn app.main:app --app-dir backend --port 8081
```

The process uses your current kubeconfig context, so use one with read-only access. `./scripts/run-scenario.sh all` creates the eight controlled failures in `inferops-demo`, and `make eval` scores them.

## Full in-cluster run on kind

```bash
make e2e            # creates kind cluster "inferops" if needed, builds and loads images, deploys, evaluates
kubectl port-forward -n inferops-demo svc/inferops-frontend 18080:80   # UI at :18080, token kind-local-token
./scripts/cleanup-scenarios.sh
```

## Triton embeddings and Qdrant locally

```bash
python3 -m venv /tmp/modelenv && /tmp/modelenv/bin/pip install torch transformers onnx onnxruntime onnxscript sentence-transformers
/tmp/modelenv/bin/python inference/triton/export_embedding_model.py      # writes model_repository/embedding
EMBEDDING_BACKEND=triton USE_QDRANT=true docker compose --profile retrieval up --build
```

The `ingest` service embeds `knowledge/` with Triton and writes it to Qdrant. The backend then retrieves with the same model. To check the served embeddings against the reference model:

```bash
PYTHONPATH=backend TRITON_HTTP_URL=http://127.0.0.1:8002 /tmp/modelenv/bin/python inference/triton/validate_triton.py
```

## Configuration

All settings are environment variables; see [`.env.example`](../.env.example). The backend validates them at startup, and `APP_ENV=production` refuses the default token.
