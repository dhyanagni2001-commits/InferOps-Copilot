"""Documentation search tool."""

from app.retrieval.retriever import Retriever
from app.schemas import Evidence


def search_docs(query: str, limit: int = 3) -> list[Evidence]:
    return Retriever().search(query, limit)
