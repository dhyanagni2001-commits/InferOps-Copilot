# Architecture

```text
Browser ──POST /api/diagnose──▶ nginx (frontend pod) ──▶ FastAPI (backend pod)
                 ◀──── SSE: status, tool_started, tool_result, completed | error

FastAPI workflow (bounded by AGENT_TIMEOUT_SECONDS, MAX_CONCURRENT_REQUESTS, rate limit)
  1. ToolRunner       kubectl get/logs as fixed argument lists, read-only RBAC, call budget
  2. rules.evaluate   normalized evidence ─▶ ordered findings, each citing evidence IDs
  3. Retriever        query embedding (hash | Triton) ─▶ local JSON index | Qdrant
  4. VLLMClient       optional; JSON-schema output, citations validated, rule fallback
```

## Evidence model

Every observation is an `Evidence` record: `id`, `source` (the tool name), `title`, a human-readable `detail`, a compact structured `data` payload, and an `error` when the tool failed. Raw kubectl JSON is normalized inside the tool (see `agent/tools/*.py`) and never forwarded whole. Rules read `data`, the UI shows `detail`, and citations refer to `id`.

| ID | Tool | Contents |
|---|---|---|
| `workload-1` | get_workload | Only produced when the workload cannot be read |
| `service-1` | service_inspect | Ports, selector, matched and ready pods, container ports, mismatches, EndpointSlice readiness |
| `status-1` | pod_status | Least healthy pod: phase, conditions, per-container state, last termination, limits, probes |
| `event-1` | pod_events | Up to 15 most recent events for that pod |
| `logs-N` | pod_logs | Bounded current or previous logs per container, plus extracted error lines |
| `doc-N` | search_docs | Runbook chunks with upstream URL and similarity score |

## Why a fixed plan instead of model-chosen tools

The evidence needed for these failure classes is always the same small set, so letting a model pick tools adds latency and failure modes without adding coverage. A fixed plan makes every API call predictable for security review and keeps the system fully functional when the model is down. The model's job is limited to explanation, and its output is checked against the collected evidence.

## Demo mode

`FixtureRunner` replays kubectl output recorded from real scenarios (`scripts/capture_fixtures.py`, stored in `backend/app/agent/fixtures/`). Demo mode therefore runs exactly the same normalization, rules, retrieval, and streaming code as cluster mode. Only the subprocess is replaced. Diagnoses in demo mode carry a limitation saying so.

## Retrieval consistency

`HashEmbedder` (offline, lexical) and `TritonEmbedder` (MiniLM via Triton) each have a `model_id`. Local indexes and Qdrant collections store it, and searching an index built by a different embedder raises `IndexMismatchError`. The workflow then degrades to "documentation unavailable" rather than returning wrong passages.

## Failure behavior

| Failure | Behavior |
|---|---|
| kubectl error or timeout on one call | That evidence record carries `error`; other evidence and rules continue |
| Workload not found or forbidden | `evidence_unavailable` with the API error |
| Previous logs unavailable | One retry, then a logs error; the crash-loop summary says the logs could not be retrieved |
| Retrieval, Triton, or Qdrant down | Diagnosis returned without docs, plus a limitation |
| vLLM down, slow, or invalid output | Rule diagnosis returned, plus a limitation |
| Overall deadline exceeded | SSE `error` event |
| Client disconnects | Generator cancelled, kubectl subprocess killed |
