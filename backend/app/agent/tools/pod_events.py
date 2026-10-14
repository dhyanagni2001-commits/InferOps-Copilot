"""Kubernetes event formatting helpers."""

from typing import Any


def summarize_events(payload: dict[str, Any]) -> str:
    items = payload.get("items", [])[-20:]
    if not items:
        return "No recent events were found."
    return "\n".join(
        f"{item.get('type', 'Normal')} {item.get('reason', 'Unknown')}: {item.get('message', '')}"
        for item in items
    )
