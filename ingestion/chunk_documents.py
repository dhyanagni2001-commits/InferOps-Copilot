"""Heading-aware chunking with an overlapping word window for long sections."""

from __future__ import annotations

import re
from typing import Any

HEADING = re.compile(r"^(#{1,3})\s+(.*)$")


def split_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in text.splitlines():
        match = HEADING.match(line)
        if match and len(match.group(1)) >= 2:
            sections.append((match.group(2).strip(), []))
        elif not (match and len(match.group(1)) == 1):
            sections[-1][1].append(line)
    return [(title, "\n".join(lines).strip()) for title, lines in sections if "\n".join(lines).strip()]


def chunk_documents(documents: list[dict[str, Any]], size: int = 180, overlap: int = 30) -> list[dict[str, Any]]:
    chunks = []
    step = max(1, size - overlap)
    for document in documents:
        for section_index, (section, body) in enumerate(split_sections(document["text"])):
            words = body.split()
            for start in range(0, max(1, len(words) - overlap), step):
                text = " ".join(words[start:start + size])
                chunks.append({
                    "id": f"{document['id']}-{section_index}-{start // step}",
                    "doc_id": document["id"],
                    "title": f"{document['title']}: {section}" if section else document["title"],
                    "section": section,
                    "url": document.get("url", ""),
                    # The section title is embedded with the text so headings contribute to recall.
                    "text": f"{section}. {text}" if section else text,
                })
    return chunks
