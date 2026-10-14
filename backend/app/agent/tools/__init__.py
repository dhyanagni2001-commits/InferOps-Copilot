"""Small read-only Kubernetes tool runner."""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.schemas import DiagnoseRequest, Evidence
from app.agent.tools.pod_events import summarize_events
from app.agent.tools.pod_logs import summarize_logs
from app.agent.tools.pod_status import label_selector, summarize_pod
from app.agent.tools.service_inspect import summarize_service

logger = logging.getLogger(__name__)


@dataclass
class ToolRunner:
    """Collect bounded evidence with kubectl or stable demo fixtures."""

    demo_mode: bool = settings.demo_mode

    async def collect(self, request: DiagnoseRequest) -> list[Evidence]:
        if self.demo_mode:
            return self._demo_evidence(request)

        resource = request.workload.kind.lower()
        name = request.workload.name
        namespace = request.namespace
        workload = await self._json_tool("workload", ["kubectl", "get", resource, name, "-n", namespace, "-o", "json"])
        if "error" in workload:
            return [self._evidence("workload-1", "workload", "Workload", workload["error"], workload)]

        if request.workload.kind == "Service":
            endpoints = await self._json_tool(
                "endpoints", ["kubectl", "get", "endpointslices", "-n", namespace, "-l", f"kubernetes.io/service-name={name}", "-o", "json"]
            )
            detail = summarize_service(workload, endpoints)
            return [self._evidence("service-1", "service_inspect", "Service inspection", detail, {"service": workload, "endpoints": endpoints})]

        pods = await self._pods_for_workload(request, workload)
        pod_items = pods.get("items", [])
        if not pod_items:
            message = pods.get("error", "No pods matched this workload.")
            return [self._evidence("status-1", "pod_status", "Pod status", message, pods)]

        # Diagnose the least healthy pod first so output remains small and relevant.
        pod = sorted(pod_items, key=self._pod_health)[0]
        pod_name = pod.get("metadata", {}).get("name", name)
        evidence = [self._evidence("status-1", "pod_status", "Pod status", summarize_pod(pod), pod)]

        events = await self._json_tool(
            "events",
            ["kubectl", "get", "events", "-n", namespace, "--field-selector", f"involvedObject.name={pod_name}", "--sort-by=.lastTimestamp", "-o", "json"],
        )
        evidence.append(self._evidence("event-1", "pod_events", "Recent pod events", summarize_events(events), events))

        previous = any(item.get("restartCount", 0) for item in pod.get("status", {}).get("containerStatuses", []))
        command = ["kubectl", "logs", pod_name, "-n", namespace, f"--tail={settings.max_log_lines}"]
        if previous:
            command.append("--previous")
        logs = await self._text_tool("logs", command)
        evidence.append(self._evidence("logs-1", "pod_logs", "Previous container logs" if previous else "Container logs", summarize_logs(logs.get("text", ""), settings.max_log_lines), logs))
        return evidence[: settings.max_tool_calls]

    async def _pods_for_workload(self, request: DiagnoseRequest, workload: dict[str, Any]) -> dict[str, Any]:
        if request.workload.kind == "Pod":
            return {"items": [workload]}
        selector = label_selector(workload)
        if not selector:
            return {"items": [], "error": "The workload has no pod label selector."}
        return await self._json_tool(
            "pods", ["kubectl", "get", "pods", "-n", request.namespace, "-l", selector, "-o", "json"]
        )

    async def _json_tool(self, source: str, command: list[str]) -> dict[str, Any]:
        result = await self._run(source, command)
        if "error" in result:
            return result
        try:
            return json.loads(result["text"])
        except json.JSONDecodeError as exc:
            return {"error": f"kubectl returned invalid JSON: {exc}"}

    async def _text_tool(self, source: str, command: list[str]) -> dict[str, Any]:
        return await self._run(source, command)

    async def _run(self, source: str, command: list[str]) -> dict[str, Any]:
        logger.info("tool_started source=%s", source)
        try:
            process = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), settings.tool_timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            logger.warning("tool_timeout source=%s", source)
            return {"error": f"{source} timed out after {settings.tool_timeout} seconds"}
        except FileNotFoundError:
            logger.warning("tool_missing source=%s", source)
            return {"error": "kubectl is not installed or is not on PATH"}

        if process.returncode:
            error = stderr.decode(errors="replace").strip()
            logger.warning("tool_failed source=%s error=%s", source, error)
            return {"error": f"kubectl failed: {error}"}
        text = stdout.decode(errors="replace")[:12000]
        logger.info("tool_completed source=%s bytes=%d", source, len(text))
        return {"text": text}

    @staticmethod
    def _evidence(identifier: str, source: str, title: str, detail: str, data: dict[str, Any]) -> Evidence:
        return Evidence(id=identifier, source=source, title=title, detail=detail, data=data)

    @staticmethod
    def _pod_health(pod: dict[str, Any]) -> tuple[int, int]:
        statuses = pod.get("status", {}).get("containerStatuses", [])
        ready = sum(int(item.get("ready", False)) for item in statuses)
        restarts = sum(item.get("restartCount", 0) for item in statuses)
        return ready, -restarts

    @staticmethod
    def _demo_evidence(request: DiagnoseRequest) -> list[Evidence]:
        question = request.question.lower()
        if "image" in question or "pull" in question:
            reason, message = "ImagePullBackOff", "Container image could not be pulled"
        elif "ready" in question or "probe" in question:
            reason, message = "Unhealthy", "Readiness probe failed with HTTP 404"
        elif "service" in question or "port" in question:
            reason, message = "PortMismatch", "Service targetPort does not match the application port"
        else:
            reason, message = "OOMKilled", "Container exceeded its configured memory limit"
        return [
            Evidence(
                id="status-1", source="pod_status", title="Container status",
                detail=f"{request.workload.name}: reason={reason}, restartCount=3",
                data={"reason": reason, "restartCount": 3},
            ),
            Evidence(
                id="event-1", source="pod_events", title="Recent event",
                detail=message, data={"reason": reason, "message": message},
            ),
        ]
