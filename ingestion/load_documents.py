"""Load allowlisted local or remote documentation sources."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

import httpx
import yaml

DEFAULT_MANIFEST = "knowledge/sources.yaml"


def html_to_text(markup: str) -> str:
    """Small HTML-to-markdown-ish conversion that keeps headings for section chunking."""
    markup = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", markup)
    markup = re.sub(r"(?i)<h([1-3])[^>]*>", lambda match: "\n" + "#" * int(match.group(1)) + " ", markup)
    markup = re.sub(r"(?i)</(p|div|li|h[1-6]|pre|tr)>", "\n", markup)
    text = html.unescape(re.sub(r"<[^>]+>", " ", markup))
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def load_documents(manifest: str = DEFAULT_MANIFEST) -> list[dict[str, Any]]:
    config = yaml.safe_load(Path(manifest).read_text())
    documents = []
    for entry in config.get("sources", []):
        if entry.get("fetch"):
            response = httpx.get(entry["url"], timeout=20, follow_redirects=True)
            response.raise_for_status()
            text = html_to_text(response.text)
        else:
            text = (Path(manifest).parent / entry["path"]).read_text()
        documents.append({**entry, "text": text, "retrieved": config.get("retrieved")})
    return documents
