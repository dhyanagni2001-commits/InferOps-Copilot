# Evaluation methodology

## Diagnostic quality (`evaluation/run_evaluation.py`)

Cases in `evaluation/datasets/cases.jsonl` target the controlled scenarios in `scenarios/`. Each case is sent to a running API and the `completed` event is scored:

| Metric | Definition |
|---|---|
| `cause_accuracy` | Diagnosis `cause` equals the expected cause |
| `keyword_recall` | Fraction of expected keywords present in the summary |
| `citation_validity` | Every cited ID resolves to a returned record without an error |
| `grounded` | A failure diagnosis cites at least one Kubernetes record, not only documentation |

Reports include the timestamp, git revision, host, and backend config (mode, LLM, retrieval). Cluster mode adds a `missing-workload` case. Use `--min-accuracy 1.0` as a regression gate; CI does this on kind.

```bash
./scripts/run-scenario.sh all          # wait until each scenario shows its failure
make eval BASE_URL=http://127.0.0.1:8081 TOKEN=dev-token
```

## Retrieval quality (`evaluation/retrieval_eval.py`)

32 natural-language queries in `evaluation/datasets/retrieval.jsonl` are labeled with the runbook that should answer them. They are paraphrases and symptoms, not copies of the runbook text. The script reports document-level hit@1, hit@3, and MRR@5 for a given embedder and store.

## Serving performance (`evaluation/benchmark_serving.py`)

A closed-loop load generator with N concurrent clients reports throughput, mean, p50, p95, max, and errors by HTTP status. Raise `RATE_LIMIT_PER_MINUTE` on the target first, or the run measures 429 responses. Throughput is bounded by `MAX_CONCURRENT_REQUESTS` (4 by default) by design.

## Reporting rules

State hardware, cluster version, mode (demo or cluster), and whether rules or the LLM produced the answer. Don't compare latency across machines or modes. Demo-mode numbers measure the application, not the Kubernetes API.
