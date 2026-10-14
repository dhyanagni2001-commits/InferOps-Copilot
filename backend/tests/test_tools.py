from app.agent.tools.pod_events import summarize_events
from app.agent.tools.pod_logs import summarize_logs
from app.agent.tools.pod_status import label_selector, summarize_pod
from app.agent.tools.service_inspect import summarize_service


def test_pod_helpers_expose_failure_reason():
    pod = {
        "metadata": {"name": "model-api-1"},
        "status": {"phase": "Running", "containerStatuses": [{
            "name": "api", "ready": False, "restartCount": 4,
            "state": {"waiting": {"reason": "CrashLoopBackOff"}},
        }]},
    }
    assert "CrashLoopBackOff" in summarize_pod(pod)
    assert summarize_logs("one\ntwo\nthree", 2) == "two\nthree"


def test_selector_and_events_are_compact():
    workload = {"spec": {"selector": {"matchLabels": {"app": "model", "tier": "api"}}}}
    events = {"items": [{"type": "Warning", "reason": "Unhealthy", "message": "probe failed"}]}
    assert label_selector(workload) == "app=model,tier=api"
    assert summarize_events(events) == "Warning Unhealthy: probe failed"


def test_service_summary_includes_ready_endpoints():
    service = {"spec": {"ports": [{"port": 80, "targetPort": 8080}]}}
    endpoints = {"items": [{"endpoints": [{"conditions": {"ready": True}}]}]}
    assert summarize_service(service, endpoints) == "Service ports: 80 -> 8080\nReady endpoints: 1"
