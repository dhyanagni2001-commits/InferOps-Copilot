import pytest

from app.agent.kubectl import CommandResult, FixtureRunner, KubectlRunner, command_shape, fixture_for
from app.agent.tools import ToolRunner, ToolStarted
from app.agent.tools.pod_events import normalize_events, summarize_events
from app.agent.tools.pod_logs import bound_logs, error_lines
from app.agent.tools.pod_status import label_selector, normalize_pod, summarize_pod
from app.agent.tools.service_inspect import normalize_service
from app.schemas import DiagnoseRequest, Evidence, Workload


def raw_pod(**status):
    return {
        "metadata": {"name": "model-api-1"},
        "spec": {"containers": [{"name": "api", "image": "img", "ports": [{"name": "http", "containerPort": 8080}],
                                 "resources": {"limits": {"memory": "1Gi"}}}]},
        "status": {"phase": "Running", "containerStatuses": [{
            "name": "api", "ready": False, "restartCount": 4,
            "state": {"waiting": {"reason": "CrashLoopBackOff"}},
            "lastState": {"terminated": {"reason": "OOMKilled", "exitCode": 137}},
        }], **status},
    }


def test_pod_summary_keeps_last_termination_reason():
    text = summarize_pod(normalize_pod(raw_pod()))
    assert "CrashLoopBackOff" in text and "lastTerminationReason=OOMKilled" in text and "memoryLimit=1Gi" in text


def test_selectors_for_workloads_and_services():
    assert label_selector({"kind": "Deployment", "spec": {"selector": {"matchLabels": {"tier": "api", "app": "m"}}}}) == "app=m,tier=api"
    assert label_selector({"kind": "Service", "spec": {"selector": {"app": "m"}}}) == "app=m"
    assert label_selector({"kind": "Deployment", "spec": {"selector": {"matchExpressions": [{"key": "a"}]}}}) == ""


def test_events_sorted_bounded_and_summarized():
    payload = {"items": [
        {"type": "Warning", "reason": "B", "message": "second", "lastTimestamp": "2026-01-02T00:00:00Z"},
        {"type": "Normal", "reason": "A", "message": "first", "lastTimestamp": "2026-01-01T00:00:00Z", "count": 2},
    ]}
    events = normalize_events(payload)
    assert [item["reason"] for item in events] == ["A", "B"]
    assert summarize_events(events).splitlines()[0] == "Normal A (x2): first"


def test_logs_are_bounded_and_errors_extracted():
    lines = bound_logs("a\nERROR boom\nc", 2)
    assert lines == ["ERROR boom", "c"]
    assert error_lines(lines) == ["ERROR boom"]


def test_service_detects_numeric_and_named_target_ports():
    pod = normalize_pod(raw_pod())
    service = {"metadata": {"name": "api"}, "spec": {"selector": {"app": "m"}, "ports": [
        {"port": 80, "targetPort": 9999}, {"port": 81, "targetPort": "http"}, {"port": 82, "targetPort": 8080},
    ]}}
    summary = normalize_service(service, {"items": []}, [pod])
    assert [item["target_port"] for item in summary["mismatched_ports"]] == [9999]


def test_command_shape_ignores_names():
    assert command_shape(["get", "pods", "-n", "x", "-l", "a=b"]) == "get pods"
    assert command_shape(["logs", "p", "--previous"]) == "logs"


async def test_kubectl_runner_refuses_mutating_verbs():
    with pytest.raises(ValueError):
        await KubectlRunner().run(["delete", "pod", "x"])


def test_fixture_selection_by_name_then_keywords():
    assert fixture_for("broken-image", "anything") == "broken-image"
    assert fixture_for("inference-demo", "Why is the readiness probe failing?") == "broken-readiness"
    assert fixture_for("inference-demo", "Why does it keep restarting?") == "oom-demo"


class CountingRunner:
    def __init__(self):
        self.calls = []

    async def run(self, args):
        self.calls.append(args)
        return CommandResult(error="forbidden")


async def test_tool_budget_and_errors_become_evidence():
    request = DiagnoseRequest(question="why?", namespace="ns", workload=Workload(kind="Deployment", name="api"))
    runner = CountingRunner()
    steps = [step async for step in ToolRunner(runner, max_calls=1).collect(request)]
    assert isinstance(steps[0], ToolStarted)
    assert steps[-1].error == "forbidden"
    assert len(runner.calls) == 1


async def test_logs_skipped_for_containers_that_never_started():
    request = DiagnoseRequest(question="why?", namespace="inferops-demo", workload=Workload(kind="Deployment", name="broken-image"))
    steps = [step async for step in ToolRunner(FixtureRunner("broken-image")).collect(request)]
    assert not [step for step in steps if isinstance(step, Evidence) and step.source == "pod_logs"]


class FlakyLogs:
    """kubectl prints this (exit 0) while a crashed container is being replaced."""

    def __init__(self):
        self.log_calls = 0

    async def run(self, args):
        if args[0] == "logs":
            self.log_calls += 1
            return CommandResult(text="unable to retrieve container logs for containerd://x" if self.log_calls == 1 else "boom\n")
        return await FixtureRunner("crashloop-demo").run(args)


async def test_unavailable_logs_are_retried_once():
    runner = FlakyLogs()
    request = DiagnoseRequest(question="why?", namespace="inferops-demo", workload=Workload(kind="Deployment", name="crashloop-demo"))
    logs = [step async for step in ToolRunner(runner).collect(request) if isinstance(step, Evidence) and step.source == "pod_logs"]
    assert runner.log_calls == 2
    assert logs[0].data["lines"] == ["boom"] and logs[0].error is None
