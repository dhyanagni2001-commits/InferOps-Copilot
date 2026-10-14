import json
from app.retrieval.embeddings import embed_text
from app.retrieval.retriever import Retriever
from app.retrieval.vector_store import LocalVectorStore


def test_local_retrieval_returns_document_evidence(tmp_path):
    records = [
        {"id": "oom-1", "title": "Memory limits", "url": "https://example.test/oom", "text": "OOMKilled means the memory limit was exceeded", "vector": embed_text("OOMKilled memory limit")},
        {"id": "probe-1", "title": "Probes", "url": "https://example.test/probes", "text": "Readiness probes control service traffic", "vector": embed_text("readiness probe")},
    ]
    path = tmp_path / "index.json"
    path.write_text(json.dumps(records))
    evidence = Retriever(LocalVectorStore(str(path))).search("memory OOMKilled", limit=1)
    assert evidence[0].title == "Memory limits"
    assert evidence[0].data["chunk_id"] == "oom-1"
