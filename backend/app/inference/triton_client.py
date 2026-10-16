"""Triton KServe v2 HTTP client for the pre-tokenized embedding model."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class TritonClient:
    def __init__(self, base_url: str | None = None, model: str | None = None, transport: httpx.BaseTransport | None = None) -> None:
        self.base_url = (base_url or settings.triton_http_url).rstrip("/")
        self.model = model or settings.triton_model
        self.http = httpx.Client(timeout=settings.tool_timeout, transport=transport)

    def ready(self) -> bool:
        try:
            return self.http.get(f"{self.base_url}/v2/models/{self.model}/ready").status_code == 200
        except httpx.HTTPError:
            return False

    def metadata(self) -> dict[str, Any]:
        response = self.http.get(f"{self.base_url}/v2/models/{self.model}")
        response.raise_for_status()
        return response.json()

    def embed_tokens(self, input_ids: list[list[int]], attention_mask: list[list[int]]) -> list[list[float]]:
        shape = [len(input_ids), len(input_ids[0])]
        payload = {
            "inputs": [
                {"name": "input_ids", "shape": shape, "datatype": "INT64", "data": input_ids},
                {"name": "attention_mask", "shape": shape, "datatype": "INT64", "data": attention_mask},
            ],
            "outputs": [{"name": "embeddings"}],
        }
        response = self.http.post(f"{self.base_url}/v2/models/{self.model}/infer", json=payload)
        response.raise_for_status()
        output = next(item for item in response.json()["outputs"] if item["name"] == "embeddings")
        rows, width = output["shape"]
        flat = output["data"]
        logger.info("triton_embedding_completed", extra={"rows": rows, "width": width})
        return [flat[index * width:(index + 1) * width] for index in range(rows)]
