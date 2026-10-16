"""Service, EndpointSlice, and backing-pod port comparison."""

from __future__ import annotations

from typing import Any


def normalize_service(service: dict[str, Any], endpoints: dict[str, Any], pods: list[dict[str, Any]]) -> dict[str, Any]:
    spec = service.get("spec", {})
    ports = [{
        "name": item.get("name"), "port": item.get("port"),
        "target_port": item.get("targetPort", item.get("port")), "protocol": item.get("protocol", "TCP"),
    } for item in spec.get("ports", [])]

    container_ports = [port for pod in pods for container in pod["containers"] for port in container["ports"]]
    numbers = {port["container_port"] for port in container_ports}
    names = {port["name"] for port in container_ports if port["name"]}
    mismatched = []
    if pods and container_ports:
        for port in ports:
            target = port["target_port"]
            if (isinstance(target, int) and target not in numbers) or (isinstance(target, str) and target not in names):
                mismatched.append(port)

    ready = not_ready = 0
    for item in endpoints.get("items", []):
        for endpoint in item.get("endpoints", []):
            if endpoint.get("conditions", {}).get("ready") is False:
                not_ready += 1
            else:
                ready += 1
    return {
        "name": service.get("metadata", {}).get("name"),
        "type": spec.get("type", "ClusterIP"),
        "selector": spec.get("selector") or {},
        "ports": ports,
        "matched_pods": len(pods),
        "ready_pods": sum(all(c["ready"] for c in pod["containers"]) and bool(pod["containers"]) for pod in pods),
        "container_ports": sorted({(p["name"] or "", p["container_port"]) for p in container_ports}),
        "mismatched_ports": mismatched,
        "ready_endpoints": ready,
        "not_ready_endpoints": not_ready,
    }


def summarize_service(summary: dict[str, Any]) -> str:
    mappings = ", ".join(f"{item['port']} -> {item['target_port']}" for item in summary["ports"]) or "none"
    container_ports = ", ".join(
        f"{name}:{number}" if name else str(number) for name, number in summary["container_ports"]
    ) or "none declared"
    lines = [
        f"Service {summary['name']} ({summary['type']}) ports: {mappings}",
        f"Selector: {summary['selector'] or 'none'} matched {summary['matched_pods']} pod(s), {summary['ready_pods']} ready",
        f"Backing container ports: {container_ports}",
        f"EndpointSlices: {summary['ready_endpoints']} ready, {summary['not_ready_endpoints']} not ready",
    ]
    for port in summary["mismatched_ports"]:
        lines.append(f"Mismatch: targetPort {port['target_port']} is not exposed by any selected container")
    return "\n".join(lines)
