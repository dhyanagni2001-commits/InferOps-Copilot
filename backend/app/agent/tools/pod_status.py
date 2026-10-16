"""Pod selection and normalized container status."""

from __future__ import annotations

from typing import Any


def label_selector(workload: dict[str, Any]) -> str:
    """Selector for Deployments, StatefulSets, DaemonSets (matchLabels) and Services (plain map)."""
    spec = workload.get("spec", {})
    selector = spec.get("selector") or {}
    labels = selector.get("matchLabels", selector) if workload.get("kind") != "Service" else selector
    if not isinstance(labels, dict):
        return ""
    return ",".join(f"{key}={value}" for key, value in sorted(labels.items()) if isinstance(value, str))


def normalize_pod(pod: dict[str, Any]) -> dict[str, Any]:
    metadata, spec, status = pod.get("metadata", {}), pod.get("spec", {}), pod.get("status", {})
    specs = {item.get("name"): item for item in spec.get("containers", [])}
    containers = []
    for item in status.get("containerStatuses", []) or [{"name": name} for name in specs]:
        container_spec = specs.get(item.get("name"), {})
        state = item.get("state", {})
        state_name = next(iter(state), "unknown")
        last = item.get("lastState", {}).get("terminated", {})
        containers.append({
            "name": item.get("name"),
            "image": item.get("image") or container_spec.get("image"),
            "ready": bool(item.get("ready", False)),
            "started": item.get("started"),
            "restart_count": item.get("restartCount", 0),
            "state": state_name,
            "reason": state.get(state_name, {}).get("reason"),
            "message": (state.get(state_name, {}).get("message") or "")[:400],
            "exit_code": state.get(state_name, {}).get("exitCode"),
            "last_reason": last.get("reason"),
            "last_exit_code": last.get("exitCode"),
            "ports": [
                {"name": port.get("name"), "container_port": port.get("containerPort")}
                for port in container_spec.get("ports", [])
            ],
            "resources": container_spec.get("resources", {}),
            "probes": [name for name in ("livenessProbe", "readinessProbe", "startupProbe") if name in container_spec],
        })
    return {
        "name": metadata.get("name", "unknown"),
        "phase": status.get("phase", "Unknown"),
        "node": spec.get("nodeName"),
        "labels": metadata.get("labels", {}),
        "conditions": [
            {key: condition.get(key) for key in ("type", "status", "reason", "message") if condition.get(key)}
            for condition in status.get("conditions", [])
        ],
        "containers": containers,
    }


def pod_health(pod: dict[str, Any]) -> tuple[int, int]:
    """Sort key: unready pods first, then pods with the most restarts."""
    containers = pod["containers"]
    ready = int(bool(containers) and all(item["ready"] for item in containers))
    return ready, -sum(item["restart_count"] for item in containers)


def summarize_pod(pod: dict[str, Any]) -> str:
    lines = [f"Pod {pod['name']}: phase={pod['phase']}"]
    for condition in pod["conditions"]:
        if condition.get("status") == "False" and condition.get("reason"):
            lines.append(f"Condition {condition['type']}=False reason={condition['reason']}: {condition.get('message', '')}".rstrip(": "))
    for item in pod["containers"]:
        line = f"Container {item['name']}: state={item['state']}, ready={str(item['ready']).lower()}, restartCount={item['restart_count']}"
        if item["reason"]:
            line += f", reason={item['reason']}"
        if item["exit_code"] is not None:
            line += f", exitCode={item['exit_code']}"
        if item["last_reason"]:
            line += f", lastTerminationReason={item['last_reason']} (exitCode={item['last_exit_code']})"
        limit = item["resources"].get("limits", {}).get("memory")
        if limit:
            line += f", memoryLimit={limit}"
        lines.append(line)
        if item["message"]:
            lines.append(f"  message: {item['message']}")
    return "\n".join(lines)
