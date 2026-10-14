"""Small Triton HTTP client for pre-tokenized embedding inputs."""

import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class TritonClient:
    async def embed_tokens(self, input_ids: list[list[int]], attention_mask: list[list[int]]) -> list[list[float]]:
        shape = [len(input_ids), len(input_ids[0])]
        payload = {"inputs": [
            {"name": "input_ids", "shape": shape, "datatype": "INT64", "data": input_ids},
            {"name": "attention_mask", "shape": shape, "datatype": "INT64", "data": attention_mask},
        ]}
        url = f"{settings.triton_http_url.rstrip('/')}/v2/models/{settings.triton_model}/infer"
        async with httpx.AsyncClient(timeout=settings.tool_timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        output = response.json()["outputs"][0]
        rows, width = output["shape"]
        flat = output["data"]
        logger.info("triton_embedding_completed rows=%d width=%d", rows, width)
        return [flat[index * width:(index + 1) * width] for index in range(rows)]
