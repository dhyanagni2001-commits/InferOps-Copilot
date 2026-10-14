"""Load allowlisted local or HTTP documentation sources."""

from pathlib import Path
from typing import Any
import httpx
import yaml


def load_documents(manifest: str = "ingestion/sources.yaml") -> list[dict[str, Any]]:
    entries = yaml.safe_load(Path(manifest).read_text()).get("sources", [])
    documents = []
    for entry in entries:
        if "path" in entry:
            text = Path(entry["path"]).read_text()
        else:
            response = httpx.get(entry["url"], timeout=20, follow_redirects=True)
            response.raise_for_status()
            text = response.text
        documents.append({**entry, "text": text})
    return documents
