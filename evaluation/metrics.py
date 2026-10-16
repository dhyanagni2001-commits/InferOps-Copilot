"""Transparent diagnostic-quality metrics."""

from __future__ import annotations

import statistics

KUBERNETES_SOURCES = {"pod_status", "pod_events", "pod_logs", "service_inspect", "get_workload"}


def score_case(expected: dict, result: dict) -> dict[str, float]:
    diagnosis = result.get("diagnosis", {})
    summary = diagnosis.get("summary", "").lower()
    keywords = [item.lower() for item in expected.get("keywords", [])]
    evidence = {item["id"]: item for item in result.get("evidence", [])}
    cited = diagnosis.get("evidence_ids", [])
    needs_citation = expected.get("cause") not in {"evidence_unavailable"}
    return {
        "cause_accuracy": float(diagnosis.get("cause") == expected.get("cause")),
        "keyword_recall": sum(item in summary for item in keywords) / max(1, len(keywords)),
        # Every cited ID must resolve to a returned, non-error record.
        "citation_validity": float(all(item in evidence and not evidence[item].get("error") for item in cited)),
        # A failure diagnosis should rest on at least one Kubernetes record, not only on documentation.
        "grounded": float(not needs_citation or any(evidence.get(item, {}).get("source") in KUBERNETES_SOURCES for item in cited)),
    }


def average(scores: list[dict[str, float]]) -> dict[str, float]:
    if not scores:
        return {}
    return {key: round(sum(item[key] for item in scores) / len(scores), 3) for key in scores[0]}


def latency_summary(durations_ms: list[float]) -> dict[str, float]:
    ordered = sorted(durations_ms)
    if not ordered:
        return {}

    def pct(p: float) -> float:
        return round(ordered[min(len(ordered) - 1, int(round(p * (len(ordered) - 1))))], 1)

    return {"mean_ms": round(statistics.mean(ordered), 1), "p50_ms": pct(0.5), "p95_ms": pct(0.95), "max_ms": round(ordered[-1], 1)}
