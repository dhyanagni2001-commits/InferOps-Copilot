"""Prompts used by the optional instruction model."""

import json
from app.schemas import DiagnoseRequest, Evidence


def diagnosis_prompt(request: DiagnoseRequest, evidence: list[Evidence]) -> str:
    records = [{"id": item.id, "source": item.source, "detail": item.detail} for item in evidence]
    return f"""You are a Kubernetes operations assistant.
Use only the evidence below. Do not invent facts or evidence identifiers.
Return JSON with two keys: summary (string) and suggested_actions (array of strings).
Keep the answer concise and state uncertainty when evidence is incomplete.

Question: {request.question}
Workload: {request.workload.kind}/{request.workload.name}
Evidence: {json.dumps(records)}
"""
