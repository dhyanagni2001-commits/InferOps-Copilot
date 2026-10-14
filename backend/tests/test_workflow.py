import pytest
from app.agent.workflow import DiagnosticWorkflow
from app.schemas import DiagnoseRequest, Evidence, Workload


class FakeTools:
    async def collect(self, request):
        return [Evidence(id="e-1", source="status", title="Status", detail="reason=OOMKilled")]


def request():
    return DiagnoseRequest(question="Why is it restarting?", namespace="inferops-demo", workload=Workload(kind="Deployment", name="demo"))


@pytest.mark.asyncio
async def test_workflow_cites_real_evidence():
    result = await DiagnosticWorkflow(FakeTools()).run("request-1", request())
    assert "memory limit" in result.diagnosis.summary
    assert result.diagnosis.evidence_ids == ["e-1"]
