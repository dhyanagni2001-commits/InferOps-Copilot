from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health/live").json() == {"status": "ok"}


def test_diagnose_stream():
    response = client.post(
        "/api/diagnose",
        headers={"Authorization": "Bearer dev-token"},
        json={"question": "Why is it restarting?", "namespace": "inferops-demo", "workload": {"kind": "Deployment", "name": "demo"}},
    )
    assert response.status_code == 200
    assert "event: completed" in response.text
    assert "OOMKilled" in response.text


def test_auth_and_namespace_are_enforced():
    payload = {"question": "Why is it broken?", "namespace": "default", "workload": {"kind": "Pod", "name": "demo"}}
    assert client.post("/api/diagnose", json=payload).status_code == 401
    assert client.post("/api/diagnose", headers={"Authorization": "Bearer dev-token"}, json=payload).status_code == 403
