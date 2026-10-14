"""Bounded evidence collection and deterministic diagnosis."""

from __future__ import annotations

import logging
from app.agent.prompts import diagnosis_prompt
from app.agent.tools import ToolRunner
from app.agent.tools.search_docs import search_docs
from app.config import settings
from app.inference.vllm_client import VLLMClient
from app.schemas import DiagnoseRequest, DiagnosticResult, Diagnosis

logger = logging.getLogger(__name__)


class DiagnosticWorkflow:
    def __init__(self, tools: ToolRunner | None = None) -> None:
        self.tools = tools or ToolRunner()

    async def run(self, request_id: str, request: DiagnoseRequest) -> DiagnosticResult:
        evidence = await self.tools.collect(request)
        evidence.extend(search_docs(f"{request.question} {request.workload.kind}"))
        joined = " ".join(item.detail.lower() for item in evidence)

        # Rules make the local path useful and testable without hallucinated citations.
        if "oomkilled" in joined or "memory limit" in joined:
            summary = "The container is restarting because it exceeded its memory limit."
            actions = ["Measure peak memory usage.", "Raise the memory limit or reduce model memory use."]
        elif "imagepull" in joined or "image could not" in joined:
            summary = "The workload cannot start because Kubernetes cannot pull its container image."
            actions = ["Verify the image name and tag.", "Check registry credentials and network access."]
        elif "readiness probe" in joined:
            summary = "The pod is running but its readiness probe is failing."
            actions = ["Verify the probe path and port.", "Test the health endpoint inside the namespace."]
        elif "portmismatch" in joined or "targetport" in joined:
            summary = "The Service target port does not match the application port."
            actions = ["Align targetPort with the container port.", "Check EndpointSlice readiness."]
        elif "crashloopbackoff" in joined or "back-off restarting" in joined:
            summary = "The container repeatedly exits and Kubernetes is delaying its restarts."
            actions = ["Inspect the previous container logs.", "Check the container command and required configuration."]
        elif "failedscheduling" in joined or "insufficient" in joined:
            summary = "Kubernetes cannot schedule the pod with the resources currently available."
            actions = ["Review pod resource requests.", "Check node capacity, taints, and affinity rules."]
        else:
            summary = "The available evidence does not identify a single root cause."
            actions = ["Inspect the returned status and events.", "Collect recent and previous container logs."]

        usable = [item.id for item in evidence if "error" not in item.data]
        limitations = [] if usable else ["Kubernetes evidence could not be collected."]
        if settings.use_llm:
            try:
                generated = await VLLMClient().diagnose(diagnosis_prompt(request, evidence))
                summary = generated["summary"]
                actions = [str(item) for item in generated["suggested_actions"][:5]]
            except Exception as exc:
                # A model outage must not hide the deterministic diagnosis.
                logger.warning("vllm_fallback request_id=%s error=%s", request_id, exc)
                limitations.append("The instruction model was unavailable; a rule-based diagnosis was returned.")
        logger.info("diagnosis_completed request_id=%s evidence_count=%d", request_id, len(evidence))
        return DiagnosticResult(
            request_id=request_id,
            diagnosis=Diagnosis(summary=summary, evidence_ids=usable, suggested_actions=actions, limitations=limitations),
            evidence=evidence,
        )
