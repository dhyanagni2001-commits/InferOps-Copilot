"""Prompts for the optional instruction model."""

from __future__ import annotations

import json

from app.agent.rules import Finding
from app.schemas import DiagnoseRequest, Evidence

SYSTEM_PROMPT = """You are a Kubernetes operations assistant that explains failures to engineers.
Rules:
- Use only the evidence records provided. Never invent facts, resource names, or evidence IDs.
- Cite evidence by its exact "id" value.
- If the evidence is insufficient, say what is missing.
- Suggest read-only checks and configuration changes; never suggest deleting data.
Respond with a single JSON object and nothing else:
{"summary": string, "evidence_ids": [string], "suggested_actions": [string]}"""


def diagnosis_messages(request: DiagnoseRequest, evidence: list[Evidence], finding: Finding) -> list[dict[str, str]]:
    records = [
        {"id": item.id, "source": item.source, "title": item.title, "detail": item.detail[:1500]}
        for item in evidence if not item.error
    ]
    user = (
        f"Question: {request.question}\n"
        f"Workload: {request.workload.kind}/{request.workload.name} in namespace {request.namespace}\n"
        f"Rule-based finding (may be incomplete): {finding.cause}: {finding.summary}\n"
        f"Evidence records:\n{json.dumps(records, indent=1)}"
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]
