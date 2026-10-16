"""Kubernetes event normalization."""

from __future__ import annotations

from typing import Any

MAX_EVENTS = 15


def normalize_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items", [])
    items = sorted(items, key=lambda item: item.get("lastTimestamp") or item.get("eventTime") or "")
    events = [{
        "type": item.get("type", "Normal"),
        "reason": item.get("reason", "Unknown"),
        "message": (item.get("message") or "").strip()[:400],
        "count": item.get("count") or item.get("series", {}).get("count") or 1,
        "last_seen": item.get("lastTimestamp") or item.get("eventTime"),
    } for item in items]
    return events[-MAX_EVENTS:]


def summarize_events(events: list[dict[str, Any]]) -> str:
    if not events:
        return "No recent events were found."
    return "\n".join(
        f"{item['type']} {item['reason']} (x{item['count']}): {item['message']}" for item in events
    )
