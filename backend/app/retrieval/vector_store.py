"""Vector stores: a local JSON index and Qdrant over its REST API."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.retrieval.embeddings import Embedder, similarity

logger = logging.getLogger(__name__)
PAYLOAD_KEYS = ("id", "title", "url", "section", "text")


class IndexMismatchError(RuntimeError):
    pass


class LocalVectorStore:
    def __init__(self, path: str, embedder: Embedder) -> None:
        self.path = Path(path)
        self.embedder = embedder
        self._records: list[dict[str, Any]] | None = None

    def write(self, records: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"model_id": self.embedder.model_id, "dimensions": self.embedder.dimensions, "records": records}
        self.path.write_text(json.dumps(payload))

    def available(self) -> bool:
        return self.path.exists()

    def _load(self) -> list[dict[str, Any]]:
        if self._records is None:
            payload = json.loads(self.path.read_text())
            if payload.get("model_id") != self.embedder.model_id:
                raise IndexMismatchError(
                    f"index {self.path} was built with {payload.get('model_id')}, not {self.embedder.model_id}; rebuild it"
                )
            self._records = payload["records"]
        return self._records

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        if not self.available():
            return []
        records = self._load()
        vector = self.embedder.embed([query])[0]
        scored = [(similarity(vector, item["vector"]), item) for item in records]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [{**{key: item.get(key) for key in PAYLOAD_KEYS}, "score": round(score, 4)} for score, item in scored[:limit]]


class QdrantVectorStore:
    def __init__(self, embedder: Embedder, url: str | None = None, collection: str | None = None) -> None:
        self.embedder = embedder
        self.url = (url or settings.qdrant_url).rstrip("/")
        self.collection = collection or settings.qdrant_collection

    def write(self, records: list[dict[str, Any]]) -> None:
        with httpx.Client(timeout=60) as client:
            client.delete(f"{self.url}/collections/{self.collection}")
            client.put(f"{self.url}/collections/{self.collection}", json={
                "vectors": {"size": self.embedder.dimensions, "distance": "Cosine"},
                "metadata": {"model_id": self.embedder.model_id},
            }).raise_for_status()
            points = [{
                # Stable IDs make re-ingestion idempotent.
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, item["id"])),
                "vector": item["vector"],
                "payload": {key: item.get(key) for key in PAYLOAD_KEYS},
            } for item in records]
            for start in range(0, len(points), 128):
                client.put(f"{self.url}/collections/{self.collection}/points", params={"wait": "true"},
                           json={"points": points[start:start + 128]}).raise_for_status()
        logger.info("qdrant_index_written", extra={"collection": self.collection, "chunks": len(records)})

    def available(self) -> bool:
        try:
            return httpx.get(f"{self.url}/collections/{self.collection}", timeout=2).status_code == 200
        except httpx.HTTPError:
            return False

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        with httpx.Client(timeout=settings.tool_timeout) as client:
            info = client.get(f"{self.url}/collections/{self.collection}")
            info.raise_for_status()
            model_id = info.json()["result"]["config"].get("metadata", {}).get("model_id")
            if model_id and model_id != self.embedder.model_id:
                raise IndexMismatchError(f"collection was built with {model_id}, not {self.embedder.model_id}")
            response = client.post(f"{self.url}/collections/{self.collection}/points/query", json={
                "query": self.embedder.embed([query])[0], "limit": limit, "with_payload": True,
            })
            response.raise_for_status()
        points = response.json().get("result", {}).get("points", [])
        return [{**item["payload"], "score": round(item.get("score", 0.0), 4)} for item in points]
