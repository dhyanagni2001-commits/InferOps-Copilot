"""Service and EndpointSlice formatting helpers."""

from typing import Any


def summarize_service(service: dict[str, Any], endpoints: dict[str, Any]) -> str:
    ports = service.get("spec", {}).get("ports", [])
    mappings = [f"{item.get('port')} -> {item.get('targetPort')}" for item in ports]
    ready = 0
    for item in endpoints.get("items", []):
        for endpoint in item.get("endpoints", []):
            ready += int(endpoint.get("conditions", {}).get("ready") is not False)
    return f"Service ports: {', '.join(mappings) or 'none'}\nReady endpoints: {ready}"
