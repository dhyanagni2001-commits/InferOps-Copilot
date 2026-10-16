import json

import httpx
import pytest

from app.inference.triton_client import TritonClient
from app.retrieval.embeddings import HashEmbedder
from app.retrieval.retriever import Retriever
from app.retrieval.vector_store import IndexMismatchError, LocalVectorStore
from ingestion.chunk_documents import chunk_documents, split_sections
from ingestion.load_documents import html_to_text


def test_local_retrieval_returns_cited_document_evidence(tmp_path):
    embedder = HashEmbedder()
    texts = ["OOMKilled means the memory limit was exceeded", "Readiness probes control service traffic"]
    records = [{"id": f"d-{i}", "title": t[:10], "url": f"https://x/{i}", "text": t, "vector": v}
               for i, (t, v) in enumerate(zip(texts, embedder.embed(texts)))]
    store = LocalVectorStore(str(tmp_path / "index.json"), embedder)
    store.write(records)
    evidence = Retriever(store).search("memory OOMKilled", limit=1)
    assert evidence[0].data["chunk_id"] == "d-0"
    assert evidence[0].data["url"] == "https://x/0"


def test_index_built_by_another_model_is_rejected(tmp_path):
    LocalVectorStore(str(tmp_path / "i.json"), HashEmbedder(128)).write([])
    with pytest.raises(IndexMismatchError):
        LocalVectorStore(str(tmp_path / "i.json"), HashEmbedder(256)).search("q")


def test_missing_index_returns_nothing(tmp_path):
    assert LocalVectorStore(str(tmp_path / "missing.json"), HashEmbedder()).search("q") == []


def test_chunks_follow_sections():
    text = "# Title\n\n## First\nalpha beta\n\n## Second\ngamma"
    assert split_sections(text) == [("First", "alpha beta"), ("Second", "gamma")]
    chunks = chunk_documents([{"id": "doc", "title": "Doc", "text": text, "url": "u"}])
    assert [chunk["title"] for chunk in chunks] == ["Doc: First", "Doc: Second"]
    assert chunks[0]["text"].startswith("First.")


def test_html_to_text_keeps_headings():
    text = html_to_text("<html><script>x()</script><h2>Probes</h2><p>Use &amp; tune</p></html>")
    assert text.splitlines() == ["## Probes", "Use & tune"]


def test_triton_client_shapes_request_and_splits_rows():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert [item["name"] for item in body["inputs"]] == ["input_ids", "attention_mask"]
        assert body["inputs"][0]["shape"] == [2, 3] and body["inputs"][0]["datatype"] == "INT64"
        return httpx.Response(200, json={"outputs": [{"name": "embeddings", "shape": [2, 2], "data": [1, 0, 0, 1]}]})

    client = TritonClient("http://triton", "embedding", transport=httpx.MockTransport(handler))
    assert client.embed_tokens([[1, 2, 3], [4, 5, 0]], [[1, 1, 1], [1, 1, 0]]) == [[1, 0], [0, 1]]
