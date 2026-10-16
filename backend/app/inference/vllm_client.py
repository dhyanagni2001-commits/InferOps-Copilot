"""OpenAI-compatible chat client for vLLM with strict output validation."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DIAGNOSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
        "suggested_actions": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
    },
    "required": ["summary", "evidence_ids", "suggested_actions"],
}


class InvalidModelOutput(ValueError):
    pass


class VLLMClient:
    def __init__(self, base_url: str | None = None, model: str | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.base_url = (base_url or settings.vllm_base_url).rstrip("/")
        self.model = model or settings.vllm_model
        self.transport = transport

    async def diagnose(self, messages: list[dict[str, str]], valid_ids: set[str]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 600,
            # vLLM constrains decoding to this schema, so parsing failures are rare but still checked.
            "response_format": {"type": "json_schema", "json_schema": {"name": "diagnosis", "schema": DIAGNOSIS_SCHEMA}},
        }
        async with httpx.AsyncClient(timeout=settings.llm_timeout, transport=self.transport) as client:
            response = await client.post(f"{self.base_url}/chat/completions", json=payload)
            response.raise_for_status()
        body = response.json()
        try:
            result = json.loads(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise InvalidModelOutput(f"model did not return JSON: {exc}") from exc
        return validate_diagnosis(result, valid_ids) | {"usage": body.get("usage", {})}


def validate_diagnosis(result: Any, valid_ids: set[str]) -> dict[str, Any]:
    """Reject output that is malformed or cites evidence the application never produced."""
    if not isinstance(result, dict):
        raise InvalidModelOutput("diagnosis must be an object")
    summary, cited, actions = result.get("summary"), result.get("evidence_ids"), result.get("suggested_actions")
    if not isinstance(summary, str) or not summary.strip():
        raise InvalidModelOutput("summary must be a non-empty string")
    if not isinstance(cited, list) or not all(isinstance(item, str) for item in cited):
        raise InvalidModelOutput("evidence_ids must be a list of strings")
    unknown = set(cited) - valid_ids
    if unknown:
        raise InvalidModelOutput(f"model cited unknown evidence: {sorted(unknown)}")
    if not cited and valid_ids:
        raise InvalidModelOutput("model cited no evidence")
    if not isinstance(actions, list) or not actions:
        raise InvalidModelOutput("suggested_actions must be a non-empty list")
    return {"summary": summary.strip(), "evidence_ids": cited, "suggested_actions": [str(item) for item in actions[:5]]}
