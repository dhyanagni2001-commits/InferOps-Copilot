"""Simple overlapping word chunker."""

from typing import Any


def chunk_documents(documents: list[dict[str, Any]], size: int = 220, overlap: int = 30) -> list[dict[str, Any]]:
    chunks = []
    step = max(1, size - overlap)
    for document in documents:
        words = document["text"].split()
        for start in range(0, len(words), step):
            text = " ".join(words[start:start + size])
            if not text:
                continue
            chunks.append({
                "id": f"{document['id']}-{start // step}", "title": document["title"],
                "url": document.get("url", document.get("path", "")), "text": text,
            })
    return chunks
