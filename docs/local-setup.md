# Local setup

The default `DEMO_MODE=true` makes the complete UI and API runnable without Kubernetes or GPU services.

```bash
python3 -m venv .venv
./.venv/bin/pip install -e './backend[dev]'
npm --prefix frontend install
./scripts/dev.sh
```

Open `http://localhost:5173` and use the default development token `dev-token`.

To inspect a real cluster, set `DEMO_MODE=false`, configure `K8S_ALLOWED_NAMESPACES`, and ensure the process has read-only `kubectl` access. Set `API_BEARER_TOKEN` to a non-default secret outside source control.
