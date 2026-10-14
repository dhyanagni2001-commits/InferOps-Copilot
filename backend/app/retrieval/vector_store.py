"""Local JSON vector index used when Qdrant is unavailable."""

import json
from pathlib import Path
from typing import Any
import httpx
from app.config import settings
from app.retrieval.embeddings import embed_text, similarity


class LocalVectorStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records = json.loads(self.path.read_text())
        query_vector = embed_text(query)
        ranked = sorted(records, key=lambda item: similarity(query_vector, item["vector"]), reverse=True)
        return ranked[:limit]


class QdrantVectorStore:
    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        url = f"{settings.qdrant_url.rstrip('/')}/collections/{settings.qdrant_collection}/points/query"
        response = httpx.post(url, timeout=settings.tool_timeout, json={
            "query": embed_text(query), "limit": limit, "with_payload": True,
        })
        response.raise_for_status()
        points = response.json().get("result", {}).get("points", [])
        return [item["payload"] for item in points]
