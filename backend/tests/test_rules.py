"""Every recorded real-cluster scenario must produce its expected root cause."""

from pathlib import Path

import pytest
import yaml

from app.agent.kubectl import FixtureRunner
from app.agent.rules import evaluate
from app.agent.tools import ToolRunner
from app.schemas import DiagnoseRequest, Evidence, Workload

CATALOG = yaml.safe_load((Path(__file__).resolve().parents[2] / "scenarios" / "scenarios.yaml").read_text())["scenarios"]


async def collect(kind: str, name: str) -> list[Evidence]:
    request = DiagnoseRequest(question="why?", namespace="inferops-demo", workload=Workload(kind=kind, name=name))
    return [step async for step in ToolRunner(FixtureRunner(name)).collect(request) if isinstance(step, Evidence)]


@pytest.mark.parametrize("scenario", CATALOG, ids=[item["name"] for item in CATALOG])
async def test_recorded_scenarios_diagnose_expected_cause(scenario):
    evidence = await collect(scenario["kind"], scenario["workload"])
    finding = evaluate(evidence, "inferops-demo", scenario["workload"])[0]
    assert finding.cause == scenario["cause"]
    known = {item.id for item in evidence}
    assert set(finding.evidence_ids) <= known
    if scenario["cause"] != "healthy":
        assert finding.evidence_ids, "a failure diagnosis must cite evidence"


async def test_oom_summary_names_limit_and_container():
    finding = evaluate(await collect("Deployment", "oom-demo"), "inferops-demo", "oom-demo")[0]
    assert "memory" in finding.summary and "32Mi" in finding.summary
    assert finding.confidence == "high"
    assert [item.cause for item in evaluate(await collect("Deployment", "oom-demo"), "inferops-demo", "oom-demo")] == ["oom_killed"]


async def test_image_pull_explains_dns_failure():
    finding = evaluate(await collect("Deployment", "broken-image"), "inferops-demo", "broken-image")[0]
    assert "does not resolve" in finding.summary
    assert finding.evidence_ids == ["status-1", "event-1"]


async def test_crash_loop_quotes_the_error_log_line():
    finding = evaluate(await collect("Deployment", "crashloop-demo"), "inferops-demo", "crashloop-demo")[0]
    assert "MODEL_PATH" in finding.summary
    assert "logs-1" in finding.evidence_ids


def status(containers, events=()):
    pod = {"name": "p", "phase": "Running", "conditions": [], "containers": containers}
    return [
        Evidence(id="status-1", source="pod_status", title="s", detail="", data={"selected": pod}),
        Evidence(id="event-1", source="pod_events", title="e", detail="", data={"events": list(events)}),
    ]


def container(**overrides):
    base = {"name": "c", "image": "i", "ready": False, "restart_count": 0, "state": "running", "reason": None,
            "message": "", "exit_code": None, "last_reason": None, "last_exit_code": None, "ports": [],
            "resources": {}, "probes": []}
    return base | overrides


def test_exit_137_with_memory_limit_is_probable_oom():
    evidence = status([container(restart_count=2, last_reason="Error", last_exit_code=137,
                                 resources={"limits": {"memory": "64Mi"}})])
    finding = evaluate(evidence, "ns", "w")[0]
    assert (finding.cause, finding.confidence) == ("oom_killed", "medium")


def test_liveness_kill_is_not_mistaken_for_oom():
    events = [{"type": "Warning", "reason": "Unhealthy", "message": "Liveness probe failed: timeout", "count": 3}]
    evidence = status([container(restart_count=2, last_exit_code=137, resources={"limits": {"memory": "1Gi"}})], events)
    assert evaluate(evidence, "ns", "w")[0].cause == "liveness_probe_failure"


def test_ready_pod_with_transient_warning_is_healthy():
    events = [{"type": "Warning", "reason": "Unhealthy", "message": "Readiness probe failed: refused", "count": 1}]
    finding = evaluate(status([container(ready=True)], events), "ns", "w")[0]
    assert finding.cause == "healthy"
    assert "did not persist" in finding.summary


def test_service_selector_matching_nothing():
    service = Evidence(id="service-1", source="service_inspect", title="s", detail="", data={
        "name": "api", "selector": {"app": "typo"}, "matched_pods": 0, "mismatched_ports": [], "container_ports": [],
    })
    assert evaluate([service], "ns", "api")[0].cause == "service_no_endpoints"


def test_missing_workload_reports_unavailable_evidence():
    missing = Evidence(id="workload-1", source="get_workload", title="w", detail="NotFound", error="NotFound")
    finding = evaluate([missing], "ns", "w")[0]
    assert finding.cause == "evidence_unavailable"
    assert finding.confidence == "low"
