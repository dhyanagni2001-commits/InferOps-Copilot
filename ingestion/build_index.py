"""Build the local index and optionally mirror it to Qdrant."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import httpx

from ingestion.chunk_documents import chunk_documents
from ingestion.load_documents import load_documents
from app.retrieval.embeddings import embed_text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def build(output: str, qdrant_url: str | None = None, collection: str = "inferops_docs") -> list[dict]:
    records = [{**chunk, "vector": embed_text(chunk["text"])} for chunk in chunk_documents(load_documents())]
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(records))
    logger.info("local_index_written path=%s chunks=%d", target, len(records))
    if qdrant_url:
        _upload_qdrant(records, qdrant_url, collection)
    return records


def _upload_qdrant(records: list[dict], base_url: str, collection: str) -> None:
    with httpx.Client(timeout=30) as client:
        client.put(f"{base_url}/collections/{collection}", json={"vectors": {"size": 128, "distance": "Cosine"}}).raise_for_status()
        points = [{"id": index, "vector": item["vector"], "payload": {key: item[key] for key in ("id", "title", "url", "text")}} for index, item in enumerate(records)]
        client.put(f"{base_url}/collections/{collection}/points", params={"wait": "true"}, json={"points": points}).raise_for_status()
    logger.info("qdrant_index_written collection=%s chunks=%d", collection, len(records))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/docs-index.json")
    parser.add_argument("--qdrant-url")
    parser.add_argument("--collection", default="inferops_docs")
    args = parser.parse_args()
    build(args.output, args.qdrant_url, args.collection)
