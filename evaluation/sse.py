"""Parse the diagnostic Server-Sent Events stream."""

from __future__ import annotations

import json


def parse_events(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields and "data" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


def completed_result(text: str) -> dict:
    for name, payload in parse_events(text):
        if name == "completed":
            return payload
        if name == "error":
            raise RuntimeError(payload.get("message", "diagnosis failed"))
    raise ValueError("response did not contain a completed event")
