"""Convert indexed documentation into normal evidence records."""

from __future__ import annotations

from app.config import settings
from app.retrieval.vector_store import LocalVectorStore, QdrantVectorStore
from app.schemas import Evidence


class Retriever:
    def __init__(self, store: LocalVectorStore | QdrantVectorStore | None = None) -> None:
        self.store = store or (QdrantVectorStore() if settings.use_qdrant else LocalVectorStore(settings.docs_index_path))

    def search(self, query: str, limit: int = 3) -> list[Evidence]:
        return [Evidence(
            id=f"doc-{index}", source="search_docs", title=item["title"], detail=item["text"],
            data={"url": item.get("url", ""), "chunk_id": item["id"]},
        ) for index, item in enumerate(self.store.search(query, limit), start=1)]
