# Technical report

## Current implementation

InferOps provides an authenticated SSE API, bounded read-only Kubernetes inspection, evidence-linked deterministic diagnoses, optional vLLM generation, local documentation retrieval, optional Qdrant indexing, and a React operator interface.

## Safety boundaries

The service account cannot read Secrets, execute inside pods, or modify workloads. Generated text does not execute commands. Namespace access, request duration, concurrency, and request rate are bounded.

## Results

No cluster, GPU, retrieval-quality, or serving-performance result is claimed until the commands in `docs/evaluation-methodology.md` are run in a recorded environment. Store raw reports under `evaluation/results/`.
