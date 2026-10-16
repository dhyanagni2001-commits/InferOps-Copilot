"""Bounded diagnostic workflow: collect evidence, apply rules, retrieve docs, optionally synthesize.

``stream`` yields ``(event_name, payload)`` pairs so the API can forward progress as it happens.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Any, Optional

from app.agent.kubectl import CommandRunner, FixtureRunner, KubectlRunner, fixture_for
from app.agent.prompts import diagnosis_messages
from app.agent.rules import Finding, evaluate
from app.agent.tools import ToolRunner, ToolStarted
from app.config import settings
from app.inference.vllm_client import VLLMClient
from app.metrics import DEPENDENCY_FAILURES, DIAGNOSES, DIAGNOSIS_DURATION
from app.retrieval.retriever import Retriever
from app.schemas import Alternative, DiagnoseRequest, Diagnosis, DiagnosticResult, Evidence

logger = logging.getLogger(__name__)

# Retrieval queries per cause; the user's question is appended for context.
DOC_QUERIES = {
    "oom_killed": "OOMKilled container exceeded memory limit exit code 137",
    "image_pull_error": "ImagePullBackOff ErrImagePull image pull registry",
    "config_error": "CreateContainerConfigError configmap secret not found",
    "unschedulable": "FailedScheduling pending pod insufficient resources taints",
    "liveness_probe_failure": "liveness probe failed restart",
    "crash_loop": "CrashLoopBackOff container exits previous logs",
    "readiness_probe_failure": "readiness probe failed endpoints not ready",
    "service_port_mismatch": "service targetPort containerPort endpoints connection refused",
    "service_no_endpoints": "service selector labels no endpoints",
}


class DiagnosticWorkflow:
    def __init__(
        self,
        runner: Optional[CommandRunner] = None,
        retriever: Optional[Retriever] = None,
        llm: Optional[VLLMClient] = None,
        demo_mode: Optional[bool] = None,
        use_llm: Optional[bool] = None,
    ) -> None:
        self.demo_mode = settings.demo_mode if demo_mode is None else demo_mode
        self.runner = runner
        self.retriever = retriever
        self.use_llm = settings.use_llm if use_llm is None else use_llm
        self.llm = llm

    async def stream(self, request_id: str, request: DiagnoseRequest) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        started = time.perf_counter()
        mode = "demo" if self.demo_mode else "cluster"
        runner = self.runner or (
            FixtureRunner(fixture_for(request.workload.name, request.question)) if self.demo_mode else KubectlRunner()
        )
        yield "status", {"request_id": request_id, "mode": mode, "message": "Collecting Kubernetes evidence"}

        evidence: list[Evidence] = []
        async for step in ToolRunner(runner).collect(request):
            if isinstance(step, ToolStarted):
                yield "tool_started", {"tool": step.tool, "args": step.args}
            else:
                evidence.append(step)
                yield "tool_result", step.model_dump()

        findings = evaluate(evidence, request.namespace, request.workload.name)
        primary = findings[0]
        limitations = [f"{item.title}: {item.error}" for item in evidence if item.error]
        if self.demo_mode:
            limitations.append("Demo mode: evidence is replayed from a recorded scenario, not read from a live cluster.")

        yield "tool_started", {"tool": "search_docs", "args": {"cause": primary.cause}}
        docs, doc_error = await self._search_docs(f"{DOC_QUERIES.get(primary.cause, '')} {request.question}")
        if doc_error:
            limitations.append(f"Documentation search unavailable: {doc_error}")
        for item in docs:
            evidence.append(item)
            yield "tool_result", item.model_dump()

        diagnosis = self._rule_diagnosis(primary, findings[1:], limitations)
        if self.use_llm:
            yield "status", {"request_id": request_id, "mode": mode, "message": "Generating explanation"}
            diagnosis = await self._llm_diagnosis(request_id, request, evidence, primary, diagnosis)

        duration = time.perf_counter() - started
        DIAGNOSES.labels(mode=mode, cause=diagnosis.cause, generated_by=diagnosis.generated_by).inc()
        DIAGNOSIS_DURATION.labels(mode=mode).observe(duration)
        logger.info("diagnosis_completed", extra={
            "request_id": request_id, "cause": diagnosis.cause, "evidence_count": len(evidence),
            "generated_by": diagnosis.generated_by, "duration_ms": round(duration * 1000, 1),
        })
        result = DiagnosticResult(request_id=request_id, mode=mode, duration_ms=round(duration * 1000, 1),
                                  diagnosis=diagnosis, evidence=evidence)
        yield "completed", result.model_dump()

    async def run(self, request_id: str, request: DiagnoseRequest) -> DiagnosticResult:
        async for name, payload in self.stream(request_id, request):
            if name == "completed":
                return DiagnosticResult.model_validate(payload)
        raise RuntimeError("workflow ended without a result")

    async def _search_docs(self, query: str) -> tuple[list[Evidence], Optional[str]]:
        try:
            retriever = self.retriever or Retriever()
            # Retrieval may call Triton and Qdrant synchronously; keep the event loop free.
            return await asyncio.to_thread(retriever.search, query, settings.docs_limit), None
        except Exception as exc:  # retrieval is advisory and must not block a diagnosis
            DEPENDENCY_FAILURES.labels(dependency="retrieval").inc()
            logger.warning("docs_search_failed", extra={"error": str(exc)})
            return [], str(exc)[:200]

    @staticmethod
    def _rule_diagnosis(primary: Finding, others: list[Finding], limitations: list[str]) -> Diagnosis:
        return Diagnosis(
            cause=primary.cause, summary=primary.summary, confidence=primary.confidence,
            evidence_ids=primary.evidence_ids, suggested_actions=primary.actions, commands=primary.commands,
            alternatives=[Alternative(cause=item.cause, summary=item.summary, evidence_ids=item.evidence_ids) for item in others],
            limitations=limitations,
        )

    async def _llm_diagnosis(
        self, request_id: str, request: DiagnoseRequest, evidence: list[Evidence], primary: Finding, fallback: Diagnosis
    ) -> Diagnosis:
        valid_ids = {item.id for item in evidence if not item.error}
        try:
            generated = await (self.llm or VLLMClient()).diagnose(diagnosis_messages(request, evidence, primary), valid_ids)
        except Exception as exc:
            # A model outage or invalid output must not hide the deterministic diagnosis.
            DEPENDENCY_FAILURES.labels(dependency="llm").inc()
            logger.warning("llm_fallback", extra={"request_id": request_id, "error": str(exc)[:300]})
            return fallback.model_copy(update={
                "limitations": fallback.limitations + [f"The instruction model was not used ({type(exc).__name__}); rule-based diagnosis returned."],
            })
        logger.info("llm_completed", extra={"request_id": request_id, "usage": generated.get("usage")})
        return fallback.model_copy(update={
            "summary": generated["summary"], "evidence_ids": generated["evidence_ids"],
            "suggested_actions": generated["suggested_actions"], "generated_by": "llm",
        })
