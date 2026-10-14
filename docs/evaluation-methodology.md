# Evaluation methodology

The checked-in dataset measures two transparent properties: expected root-cause keywords and whether every cited evidence ID resolves to a returned record.

```bash
python -m evaluation.run_evaluation
python -m evaluation.benchmark_serving --count 20
```

Run the same cases in demo mode for regression testing and against controlled Kubernetes scenarios for real evidence validation. Report hardware, model revision, configuration, case count, mean latency, p95 latency, and both quality metrics. Do not compare performance across different hardware without stating the difference.
