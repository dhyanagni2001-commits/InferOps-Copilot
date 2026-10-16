"""Bounded, read-only Kubernetes evidence collection.

The plan is fixed by the workload kind rather than proposed by a model, so every
kubectl call is a known argument list built from validated request fields.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Union

from app.agent.kubectl import CommandResult, CommandRunner
from app.agent.tools.pod_events import normalize_events, summarize_events
from app.agent.tools.pod_logs import bound_logs, error_lines, summarize_logs
from app.agent.tools.pod_status import label_selector, normalize_pod, pod_health, summarize_pod
from app.agent.tools.service_inspect import normalize_service, summarize_service
from app.config import settings
from app.schemas import DiagnoseRequest, Evidence

UNAVAILABLE_LOGS = "unable to retrieve container logs"
RESOURCE_NAMES = {
    "Deployment": "deployment", "StatefulSet": "statefulset", "DaemonSet": "daemonset",
    "Pod": "pod", "Service": "service",
}


@dataclass
class ToolStarted:
    tool: str
    args: dict[str, Any]


Step = Union[ToolStarted, Evidence]


@dataclass
class ToolRunner:
    runner: CommandRunner
    max_calls: int = field(default_factory=lambda: settings.max_tool_calls)

    async def collect(self, request: DiagnoseRequest) -> AsyncIterator[Step]:
        self.calls = 0
        namespace, kind, name = request.namespace, request.workload.kind, request.workload.name

        yield ToolStarted("get_workload", {"kind": kind, "name": name})
        workload = await self._kubectl(["get", RESOURCE_NAMES[kind], name, "-n", namespace, "-o", "json"])
        if workload.error:
            yield Evidence(id="workload-1", source="get_workload", title=f"{kind} {name}",
                           detail=workload.error, error=workload.error)
            return

        workload_json = workload.json()
        if kind == "Service":
            async for step in self._service(namespace, workload_json):
                yield step
            return

        pods = await self._pods(namespace, kind, workload_json)
        async for step in self._pod_evidence(namespace, name, pods):
            yield step

    async def _service(self, namespace: str, service: dict[str, Any]) -> AsyncIterator[Step]:
        name = service.get("metadata", {}).get("name", "")
        yield ToolStarted("service_inspect", {"service": name})
        endpoints = await self._kubectl(
            ["get", "endpointslices", "-n", namespace, "-l", f"kubernetes.io/service-name={name}", "-o", "json"]
        )
        selector = label_selector(service)
        pods: list[dict[str, Any]] = []
        if selector:
            result = await self._kubectl(["get", "pods", "-n", namespace, "-l", selector, "-o", "json"])
            pods = [normalize_pod(item) for item in result.json().get("items", [])]
        summary = normalize_service(service, endpoints.json(), pods)
        yield Evidence(id="service-1", source="service_inspect", title=f"Service {name}",
                       detail=summarize_service(summary), data=summary, error=endpoints.error)
        # A Service with unready backends is usually explained by the backing pods themselves.
        if pods and summary["ready_pods"] < len(pods):
            async for step in self._pod_evidence(namespace, name, pods):
                yield step

    async def _pods(self, namespace: str, kind: str, workload: dict[str, Any]) -> list[dict[str, Any]]:
        if kind == "Pod":
            return [normalize_pod(workload)]
        selector = label_selector(workload)
        if not selector:
            return []
        result = await self._kubectl(["get", "pods", "-n", namespace, "-l", selector, "-o", "json"])
        return [normalize_pod(item) for item in result.json().get("items", [])]

    async def _pod_evidence(self, namespace: str, name: str, pods: list[dict[str, Any]]) -> AsyncIterator[Step]:
        yield ToolStarted("pod_status", {"workload": name, "pods": len(pods)})
        if not pods:
            message = "No pods matched the workload selector."
            yield Evidence(id="status-1", source="pod_status", title="Pod status", detail=message,
                           data={"pods": [], "total": 0})
            return

        pod = sorted(pods, key=pod_health)[0]
        ready = sum(pod_health(item)[0] for item in pods)
        yield Evidence(
            id="status-1", source="pod_status", title=f"Pod status ({ready}/{len(pods)} ready)",
            detail=summarize_pod(pod), data={"selected": pod, "total": len(pods), "ready": ready},
        )

        yield ToolStarted("pod_events", {"pod": pod["name"]})
        events = await self._kubectl(
            ["get", "events", "-n", namespace, "--field-selector", f"involvedObject.name={pod['name']}", "-o", "json"]
        )
        normalized = normalize_events(events.json())
        yield Evidence(id="event-1", source="pod_events", title=f"Events for {pod['name']}",
                       detail=events.error or summarize_events(normalized), data={"events": normalized},
                       error=events.error)

        for index, container in enumerate(pod["containers"][:2], start=1):
            # Containers that never started have no logs; their failure is in status and events.
            if container["state"] == "waiting" and not container["restart_count"]:
                continue
            previous = container["restart_count"] > 0
            yield ToolStarted("pod_logs", {"pod": pod["name"], "container": container["name"], "previous": previous})
            command = ["logs", pod["name"], "-n", namespace, "-c", container["name"], f"--tail={settings.max_log_lines}"]
            if previous:
                command.append("--previous")
            logs = await self._logs(command)
            lines = bound_logs(logs.text, settings.max_log_lines)
            label = "Previous" if previous else "Current"
            yield Evidence(
                id=f"logs-{index}", source="pod_logs", title=f"{label} logs: {container['name']}",
                detail=logs.error or summarize_logs(lines),
                data={"container": container["name"], "previous": previous, "lines": lines, "errors": error_lines(lines)},
                error=logs.error,
            )

    async def _logs(self, command: list[str]) -> CommandResult:
        result = await self._kubectl(command)
        # While a crashing container is being replaced, kubectl can exit 0 with this message instead of logs.
        if result.text.startswith(UNAVAILABLE_LOGS):
            await asyncio.sleep(0.2)
            result = await self._kubectl(command)
            if result.text.startswith(UNAVAILABLE_LOGS):
                return CommandResult(error=result.text.strip()[:300])
        return result

    async def _kubectl(self, args: list[str]) -> CommandResult:
        if self.calls >= self.max_calls:
            return CommandResult(error=f"tool call budget of {self.max_calls} exhausted")
        self.calls += 1
        return await self.runner.run(args)
