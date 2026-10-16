# Technical report

Measured 2026-10-15. Raw JSON for every number is in `evaluation/results/`.

## Environment

| Item | Value |
|---|---|
| Host | Apple Silicon (arm64), macOS 27.0.1, Colima VM with 6 vCPU / 10 GB |
| Cluster | kind v0.33.0, Kubernetes v1.37.0, single node, kindnet CNI |
| Backend | v0.2.0, Python 3.12, rule-based answers (`USE_LLM=false`) |
| Triton | 25.08-py3 (arm64), ONNX Runtime backend, CPU instance |
| Qdrant | v1.15.5 |
| Embedding model | all-MiniLM-L6-v2 @ c9745ed, exported with torch 2.14.1, validated with onnxruntime 1.31.0 |

## 1. Diagnostic quality on a live cluster

Eight controlled scenarios ran in `inferops-demo`, plus a nonexistent workload. The backend ran in-cluster under its read-only ServiceAccount and was reached through the nginx frontend (`scripts/kind-e2e.sh`). Result file: `kind-e2e.json`.

| Case | Expected | Result | Latency |
|---|---|---|---|
| oom | oom_killed | ✓ | 134 ms |
| image-pull | image_pull_error | ✓ | 82 ms |
| readiness | readiness_probe_failure | ✓ | 111 ms |
| service-port | service_port_mismatch | ✓ | 80 ms |
| crash-loop | crash_loop | ✓ | 111 ms |
| unschedulable | unschedulable | ✓ | 107 ms |
| missing-config | config_error | ✓ | 88 ms |
| healthy | healthy | ✓ | 121 ms |
| missing-workload | evidence_unavailable | ✓ | 32 ms |

Cause accuracy 1.0, citation validity 1.0, grounded 1.0, keyword recall 1.0.

An earlier run from the host's kubectl (`cluster-local-kubectl.json`) also scored 9/9 on cause but 0.944 on keyword recall. Previous-container logs for the crash-loop pod were unavailable at that moment, so the `MODEL_PATH` line was missing from the summary. Recording real clusters exposed three behaviors that synthetic tests would have missed, and each now has a rule or tool fix and a regression test:

1. An OOM kill was reported as `state.terminated.reason: Error, exitCode: 137`, with `OOMKilled` only in `lastState`. The original summary code also dropped `lastState` whenever the container was waiting.
2. `kubectl logs --previous` can exit 0 and print `unable to retrieve container logs for containerd://…`. It is now treated as an error, with one retry.
3. A healthy pod keeps a `Warning Unhealthy` event from its first readiness probe, so "no warnings" was the wrong health test.

Security checks in the same run: `kubectl auth can-i` returns `no` for `delete pods`, `create deployments`, and `get secrets` as the backend ServiceAccount. A pod without the frontend label can't reach the backend (the NetworkPolicy is enforced by kindnet).

## 2. Embedding export and serving fidelity

| Comparison | Texts | Min cosine | Max abs diff |
|---|---|---|---|
| ONNX Runtime vs PyTorch (`triton-export-report.json`) | 4 | 0.99999994 | 2.2e-7 |
| Rust tokenizer + Triton vs sentence-transformers (`triton-validation.json`) | 5, including one truncated at 256 tokens | 0.99999997 | 3.9e-7 |

Pooling (attention-masked mean) and L2 normalization are inside the ONNX graph, so clients only tokenize.

## 3. Retrieval quality

32 labeled queries over 8 runbooks (32 chunks):

| Embedder | Store | hit@1 | hit@3 | MRR@5 | Mean query time |
|---|---|---|---|---|---|
| Feature hashing (256-d, uni+bigrams) | local JSON | 0.594 | 0.812 | 0.709 | 0.2 ms |
| MiniLM via Triton (384-d) | local JSON | 0.906 | 1.000 | 0.948 | 5.0 ms |
| MiniLM via Triton (384-d) | Qdrant | 0.906 | 1.000 | 0.948 | 13.8 ms |

Qdrant and brute-force local search return identical rankings at this corpus size. Query time includes the Triton round trip. The query set was written for this corpus, so it is small and the figures are relative.

## 4. API performance

Closed-loop clients with the rate limit raised for the run; `MAX_CONCURRENT_REQUESTS=4`; no request failed.

| Deployment | Concurrency | Throughput | p50 | p95 |
|---|---|---|---|---|
| kind, live kubectl, `oom-demo` | 1 | 8.4 rps | 103 ms | 344 ms |
| | 4 | 30.2 rps | 129 ms | 147 ms |
| | 8 | 30.4 rps | 259 ms | 284 ms |
| kind, live kubectl, `healthy-demo` | 1 | 9.5 rps | 103 ms | 118 ms |
| | 8 | 30.9 rps | 255 ms | 273 ms |
| Compose, demo replay + Triton + Qdrant | 1 | 17.5 rps | 58 ms | 62 ms |
| | 4 | 62.0 rps | 64 ms | 72 ms |
| | 8 | 70.9 rps | 111 ms | 130 ms |

In cluster mode, latency is dominated by 4–5 sequential `kubectl` subprocesses against the API server (about 20 ms each). Throughput plateaus at about 30 rps because of the 4-slot concurrency limit, a deliberate cap on API-server load. The single-client OOM p95 includes the 0.2 s retry when previous logs are unavailable. Demo-mode numbers measure the application only.

## 5. Not yet measured

- vLLM generation quality, JSON validity rate, and latency on a GPU. The code path is tested only against a mocked server.
- The GPU overlay applied to a real GPU node.
- Multi-node clusters, and namespaces with many pods or events (outputs are capped, but not load-tested at that scale).

## Safety boundaries

The ServiceAccount can only `get`, `list`, and `watch` pods, logs, events, services, EndpointSlices, and workloads in allowed namespaces. It has no Secret access, no exec, and no writes. The runner refuses any kubectl verb other than `get` and `logs`, and arguments come only from validated names. Generated text is never executed. Model output cannot introduce citations to evidence that wasn't collected.
