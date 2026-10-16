import dataclasses
import json

from fastapi.testclient import TestClient

from app.api import chat
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-token-123"}


def payload(name="oom-demo", namespace="inferops-demo", kind="Deployment"):
    return {"question": "Why is it restarting?", "namespace": namespace, "workload": {"kind": kind, "name": name}}


def events(text: str) -> list[tuple[str, dict]]:
    parsed = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        parsed.append((lines["event"], json.loads(lines["data"])))
    return parsed


def test_health_and_config():
    assert client.get("/health/live").json() == {"status": "ok"}
    ready = client.get("/health/ready")
    assert ready.status_code == 200 and ready.json()["checks"]["docs_index"] is True
    config = client.get("/api/config").json()
    assert config["mode"] == "demo" and config["allowed_namespaces"] == ["inferops-demo"]


def test_metrics_exposed():
    client.post("/api/diagnose", headers=AUTH, json=payload())
    assert "inferops_diagnoses_total" in client.get("/metrics").text


def test_diagnose_streams_evidence_then_result():
    response = client.post("/api/diagnose", headers=AUTH, json=payload("broken-image"))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    stream = events(response.text)
    names = [name for name, _ in stream]
    assert names[0] == "status" and names[-1] == "completed" and "tool_started" in names
    result = stream[-1][1]
    assert result["diagnosis"]["cause"] == "image_pull_error"
    assert result["request_id"] == response.headers["x-request-id"]
    assert {item["id"] for item in result["evidence"]} >= set(result["diagnosis"]["evidence_ids"])


def test_auth_is_enforced():
    assert client.post("/api/diagnose", json=payload()).status_code == 401
    assert client.post("/api/diagnose", headers={"Authorization": "Bearer wrong"}, json=payload()).status_code == 401
    assert client.post("/api/diagnose", headers={"Authorization": "Basic test-token-123"}, json=payload()).status_code == 401


def test_namespace_allowlist_and_validation():
    assert client.post("/api/diagnose", headers=AUTH, json=payload(namespace="kube-system")).status_code == 403
    assert client.post("/api/diagnose", headers=AUTH, json=payload(name="Bad_Name")).status_code == 422
    assert client.post("/api/diagnose", headers=AUTH, json=payload(kind="Secret")).status_code == 422
    oversized = payload() | {"question": "x" * 2001}
    assert client.post("/api/diagnose", headers=AUTH, json=oversized).status_code == 422


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(chat, "rate_limiter", chat.RateLimiter(1))
    assert client.post("/api/diagnose", headers=AUTH, json=payload()).status_code == 200
    assert client.post("/api/diagnose", headers=AUTH, json=payload()).status_code == 429


def test_timeout_becomes_error_event(monkeypatch):
    monkeypatch.setattr(chat, "settings", dataclasses.replace(chat.settings, request_timeout=0.0))
    stream = events(client.post("/api/diagnose", headers=AUTH, json=payload()).text)
    assert stream[-1][0] == "error" and "timed out" in stream[-1][1]["message"]
