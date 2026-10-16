"""Embed documentation chunks and write the local index and, optionally, Qdrant."""

from __future__ import annotations

import argparse
import logging

from app.retrieval.embeddings import Embedder, HashEmbedder, TritonEmbedder
from app.retrieval.vector_store import LocalVectorStore, QdrantVectorStore
from ingestion.chunk_documents import chunk_documents
from ingestion.load_documents import DEFAULT_MANIFEST, load_documents

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("ingestion")


def make_embedder(backend: str) -> Embedder:
    return TritonEmbedder() if backend == "triton" else HashEmbedder()


def build(output: str | None, qdrant_url: str | None, collection: str, backend: str, manifest: str) -> list[dict]:
    embedder = make_embedder(backend)
    chunks = chunk_documents(load_documents(manifest))
    vectors = embedder.embed([chunk["text"] for chunk in chunks])
    records = [{**chunk, "vector": vector} for chunk, vector in zip(chunks, vectors)]
    if output:
        LocalVectorStore(output, embedder).write(records)
        logger.info("local index written: path=%s chunks=%d model=%s", output, len(records), embedder.model_id)
    if qdrant_url:
        QdrantVectorStore(embedder, qdrant_url, collection).write(records)
        logger.info("qdrant index written: collection=%s chunks=%d", collection, len(records))
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/docs-index.json", help="local JSON index path ('' to skip)")
    parser.add_argument("--qdrant-url", help="also upload to this Qdrant instance")
    parser.add_argument("--collection", default="inferops_docs")
    parser.add_argument("--embedding-backend", choices=["hash", "triton"], default="hash")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    build(args.output or None, args.qdrant_url, args.collection, args.embedding_backend, args.manifest)


if __name__ == "__main__":
    main()
