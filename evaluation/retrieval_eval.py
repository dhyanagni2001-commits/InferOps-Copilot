"""Measure document-level retrieval quality (hit@1, hit@3, MRR) for the configured embedder and store."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from app.retrieval.embeddings import HashEmbedder, TritonEmbedder
from app.retrieval.vector_store import LocalVectorStore, QdrantVectorStore


def evaluate(store, cases: list[dict], depth: int = 5) -> dict:
    hits1 = hits3 = reciprocal = 0.0
    misses = []
    started = time.perf_counter()
    for case in cases:
        docs = [item["id"].rsplit("-", 2)[0] for item in store.search(case["query"], depth)]
        rank = docs.index(case["doc"]) + 1 if case["doc"] in docs else None
        hits1 += rank == 1
        hits3 += rank is not None and rank <= 3
        reciprocal += 1 / rank if rank else 0
        if rank != 1:
            misses.append({"query": case["query"], "expected": case["doc"], "got": docs[:3]})
    count = len(cases)
    return {
        "cases": count, "hit@1": round(hits1 / count, 3), "hit@3": round(hits3 / count, 3),
        "mrr@5": round(reciprocal / count, 3), "mean_query_ms": round((time.perf_counter() - started) * 1000 / count, 2),
        "misses": misses,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embedding-backend", choices=["hash", "triton"], default="hash")
    parser.add_argument("--index", default="data/docs-index.json")
    parser.add_argument("--qdrant-url", help="search this Qdrant instance instead of the local index")
    parser.add_argument("--collection", default="inferops_docs")
    parser.add_argument("--dataset", default="evaluation/datasets/retrieval.jsonl")
    parser.add_argument("--output")
    args = parser.parse_args()
    embedder = TritonEmbedder() if args.embedding_backend == "triton" else HashEmbedder()
    store = QdrantVectorStore(embedder, args.qdrant_url, args.collection) if args.qdrant_url else LocalVectorStore(args.index, embedder)
    cases = [json.loads(line) for line in Path(args.dataset).read_text().splitlines() if line.strip()]
    report = {"embedder": embedder.model_id, "store": "qdrant" if args.qdrant_url else "local", **evaluate(store, cases)}
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "misses"}, indent=2))


if __name__ == "__main__":
    main()
