import json

import httpx

from app.agent.kubectl import FixtureRunner
from app.agent.workflow import DiagnosticWorkflow
from app.inference.vllm_client import VLLMClient
from app.schemas import DiagnoseRequest, Evidence, Workload


def request(name="oom-demo", kind="Deployment"):
    return DiagnoseRequest(question="Why is it restarting?", namespace="inferops-demo", workload=Workload(kind=kind, name=name))


class StubRetriever:
    def search(self, query, limit=3):
        return [Evidence(id="doc-1", source="search_docs", title="OOM", detail="memory", data={"url": "https://x"})]


class BrokenRetriever:
    def search(self, query, limit=3):
        raise ConnectionError("qdrant down")


def llm(content: str, status: int = 200) -> VLLMClient:
    def handler(http_request: httpx.Request) -> httpx.Response:
        body = json.loads(http_request.content)
        assert body["response_format"]["type"] == "json_schema"
        return httpx.Response(status, json={"choices": [{"message": {"content": content}}], "usage": {"total_tokens": 9}})
    return VLLMClient(base_url="http://vllm/v1", transport=httpx.MockTransport(handler))


async def test_stream_emits_progress_before_completion():
    workflow = DiagnosticWorkflow(retriever=StubRetriever(), demo_mode=True, use_llm=False)
    events = [name async for name, _ in workflow.stream("r-1", request())]
    assert events[0] == "status"
    assert events.index("tool_started") < events.index("tool_result") < events.index("completed")
    assert events[-1] == "completed"


async def test_rule_diagnosis_cites_only_returned_evidence():
    result = await DiagnosticWorkflow(retriever=StubRetriever(), demo_mode=True, use_llm=False).run("r-1", request())
    assert result.mode == "demo" and result.diagnosis.cause == "oom_killed"
    assert set(result.diagnosis.evidence_ids) <= {item.id for item in result.evidence}
    assert any(item.source == "search_docs" for item in result.evidence)


async def test_retrieval_outage_degrades_to_limitation():
    result = await DiagnosticWorkflow(retriever=BrokenRetriever(), demo_mode=True, use_llm=False).run("r-1", request())
    assert result.diagnosis.cause == "oom_killed"
    assert any("Documentation search unavailable" in item for item in result.diagnosis.limitations)


async def test_llm_answer_is_used_when_citations_are_valid():
    content = json.dumps({"summary": "Memory limit exceeded.", "evidence_ids": ["status-1", "doc-1"], "suggested_actions": ["Raise limit"]})
    workflow = DiagnosticWorkflow(retriever=StubRetriever(), llm=llm(content), demo_mode=True, use_llm=True)
    result = await workflow.run("r-1", request())
    assert result.diagnosis.generated_by == "llm"
    assert result.diagnosis.summary == "Memory limit exceeded."
    assert result.diagnosis.cause == "oom_killed"


async def test_llm_hallucinated_citation_falls_back_to_rules():
    content = json.dumps({"summary": "x", "evidence_ids": ["status-99"], "suggested_actions": ["y"]})
    workflow = DiagnosticWorkflow(retriever=StubRetriever(), llm=llm(content), demo_mode=True, use_llm=True)
    result = await workflow.run("r-1", request())
    assert result.diagnosis.generated_by == "rules"
    assert any("InvalidModelOutput" in item for item in result.diagnosis.limitations)


async def test_llm_outage_falls_back_to_rules():
    workflow = DiagnosticWorkflow(retriever=StubRetriever(), llm=llm("", status=503), demo_mode=True, use_llm=True)
    result = await workflow.run("r-1", request())
    assert result.diagnosis.generated_by == "rules"
    assert any("HTTPStatusError" in item for item in result.diagnosis.limitations)


async def test_injected_runner_is_used_for_cluster_mode():
    workflow = DiagnosticWorkflow(runner=FixtureRunner("broken-service"), retriever=StubRetriever(), demo_mode=False, use_llm=False)
    result = await workflow.run("r-1", request("broken-service", "Service"))
    assert result.mode == "cluster"
    assert result.diagnosis.cause == "service_port_mismatch"
