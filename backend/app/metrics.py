"""Prometheus metrics exposed at /metrics."""

from prometheus_client import Counter, Histogram

DIAGNOSES = Counter("inferops_diagnoses_total", "Completed diagnostic requests", ["mode", "cause", "generated_by"])
DIAGNOSIS_FAILURES = Counter("inferops_diagnosis_failures_total", "Diagnostic requests that ended in an error", ["reason"])
DIAGNOSIS_DURATION = Histogram(
    "inferops_diagnosis_duration_seconds", "End-to-end diagnosis latency", ["mode"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)
TOOL_DURATION = Histogram(
    "inferops_kubectl_duration_seconds", "kubectl call latency", ["command"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)
DEPENDENCY_FAILURES = Counter("inferops_dependency_failures_total", "Optional dependency failures", ["dependency"])
