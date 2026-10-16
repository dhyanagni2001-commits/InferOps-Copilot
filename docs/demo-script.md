# Demo script (about 5 minutes)

1. `make dev`, open http://localhost:5173. Point out the **demo replay** badge: recorded real-cluster output, same code path.
2. Run **OOM restart**. Show the live steps, the high-confidence finding naming the 32Mi limit, the `status-1` citation jumping to the opened evidence, and the copyable `kubectl` commands.
3. Run **Service port**. The pods are healthy, but `targetPort 9999` doesn't match container port 80; explain the EndpointSlice and container-port comparison.
4. Run **Healthy**. There's no false alarm, and the transient readiness warning from startup is mentioned, not blamed.
5. Switch to the live cluster: `make e2e`, then `kubectl port-forward -n inferops-demo svc/inferops-frontend 18080:80` (token `kind-local-token`). The badge now says **live cluster**. Run **Crash loop** and show the `MODEL_PATH` error quoted from `--previous` logs.
6. Show safety: `kubectl auth can-i delete pods --as=system:serviceaccount:inferops-demo:inferops-backend` returns `no`, and the namespace allowlist returns 403 for `kube-system`.
7. Show `curl localhost:8081/metrics | grep inferops_` and a JSON log line with the request ID.
8. Close on `evaluation/results/`: 9/9 in-cluster, and the retrieval hit@1 gain from Triton embeddings.

State clearly that answers are rule-based unless `USE_LLM=true` with a running vLLM.
