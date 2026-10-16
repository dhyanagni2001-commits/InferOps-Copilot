"""Test configuration: environment is fixed before the app is imported."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "backend" / ".pytest_cache" / "docs-index.json"

os.environ.update({
    "DEMO_MODE": "true", "USE_LLM": "false", "USE_QDRANT": "false", "EMBEDDING_BACKEND": "hash",
    "API_BEARER_TOKEN": "test-token-123", "RATE_LIMIT_PER_MINUTE": "1000", "DOCS_INDEX_PATH": str(INDEX),
})
sys.path.insert(0, str(ROOT))

from ingestion.build_index import build  # noqa: E402

build(str(INDEX), None, "unused", "hash", str(ROOT / "knowledge" / "sources.yaml"))
