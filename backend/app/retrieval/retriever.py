"""Convert indexed documentation into citable evidence records."""

from __future__ import annotations

from typing import Optional, Union

from app.config import settings
from app.retrieval.embeddings import get_embedder
from app.retrieval.vector_store import LocalVectorStore, QdrantVectorStore
from app.schemas import Evidence

Store = Union[LocalVectorStore, QdrantVectorStore]


def default_store() -> Store:
    embedder = get_embedder()
    if settings.use_qdrant:
        return QdrantVectorStore(embedder)
    return LocalVectorStore(settings.docs_index_path, embedder)


class Retriever:
    def __init__(self, store: Optional[Store] = None) -> None:
        self.store = store or default_store()

    def search(self, query: str, limit: int = 3) -> list[Evidence]:
        return [Evidence(
            id=f"doc-{index}", source="search_docs", title=item["title"],
            detail=item["text"][:900] + ("…" if len(item["text"]) > 900 else ""),
            data={"url": item.get("url") or "", "chunk_id": item["id"], "section": item.get("section"), "score": item.get("score")},
        ) for index, item in enumerate(self.store.search(query, limit), start=1)]
