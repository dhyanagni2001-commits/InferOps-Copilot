# Local setup

The default `DEMO_MODE=true` makes the complete UI and API runnable without Kubernetes or GPU services.

```bash
python3 -m venv .venv
./.venv/bin/pip install -e './backend[dev]'
npm --prefix frontend install
./scripts/dev.sh
```

Open `http://localhost:5173` and use the default development token `dev-token`.
The local backend listens on `http://127.0.0.1:8081`.

To inspect a real cluster, set `DEMO_MODE=false`, configure `K8S_ALLOWED_NAMESPACES`, and ensure the process has read-only `kubectl` access. Set `API_BEARER_TOKEN` to a non-default secret outside source control.

Build and enable documentation retrieval with:

```bash
./.venv/bin/python -m ingestion.build_index
# Optional Qdrant mirror:
./.venv/bin/python -m ingestion.build_index --qdrant-url http://127.0.0.1:6333
```

Set `USE_QDRANT=true` to query Qdrant or leave it false to read `data/docs-index.json`. Set `USE_LLM=true` only when the configured vLLM endpoint is available.
