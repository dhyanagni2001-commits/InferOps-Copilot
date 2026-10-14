"""Minimal OpenAI-compatible vLLM client."""

import json
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class VLLMClient:
    async def diagnose(self, prompt: str) -> dict:
        payload = {
            "model": settings.vllm_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 500,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.post(f"{settings.vllm_base_url.rstrip('/')}/chat/completions", json=payload)
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        result = json.loads(content)
        if not isinstance(result.get("summary"), str) or not isinstance(result.get("suggested_actions"), list):
            raise ValueError("vLLM returned an invalid diagnosis")
        logger.info("vllm_completed model=%s", settings.vllm_model)
        return result
