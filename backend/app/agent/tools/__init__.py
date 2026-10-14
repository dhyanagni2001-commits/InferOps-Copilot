"""Small read-only Kubernetes tool runner."""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.schemas import DiagnoseRequest, Evidence

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
        commands = [
            ("status", ["kubectl", "get", resource, name, "-n", namespace, "-o", "json"]),
            ("events", ["kubectl", "get", "events", "-n", namespace, "--sort-by=.lastTimestamp", "-o", "json"]),
        ]
        results: list[Evidence] = []
        for index, (source, command) in enumerate(commands[: settings.max_tool_calls], start=1):
            logger.info("tool_started source=%s namespace=%s workload=%s", source, namespace, name)
            detail, data = await self._run(command)
            results.append(Evidence(id=f"{source}-{index}", source=source, title=source.title(), detail=detail, data=data))
            logger.info("tool_completed source=%s bytes=%d", source, len(detail))
        return results

    async def _run(self, command: list[str]) -> tuple[str, dict[str, Any]]:
        try:
            process = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), settings.tool_timeout)
        except (FileNotFoundError, asyncio.TimeoutError) as exc:
            logger.warning("tool_failed error=%s", exc)
            return f"Tool unavailable: {exc}", {"error": str(exc)}

        text = stdout.decode(errors="replace")
        if process.returncode:
            error = stderr.decode(errors="replace").strip()
            return f"kubectl failed: {error}", {"error": error}
        data = json.loads(text)
        # Keep streamed evidence bounded even if a namespace has many events.
        if isinstance(data.get("items"), list):
            data["items"] = data["items"][-20:]
        return json.dumps(data, separators=(",", ":"))[:12000], data

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
