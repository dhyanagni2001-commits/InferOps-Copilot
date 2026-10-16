import pytest

from app.config import Settings


def test_production_rejects_default_token(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_BEARER_TOKEN", "dev-token")
    with pytest.raises(RuntimeError, match="development default"):
        Settings().validate()


def test_unknown_embedding_backend_rejected(monkeypatch):
    monkeypatch.setenv("EMBEDDING_BACKEND", "openai")
    with pytest.raises(RuntimeError):
        Settings().validate()


def test_namespace_list_parsing(monkeypatch):
    monkeypatch.setenv("K8S_ALLOWED_NAMESPACES", " a, b ,,")
    assert Settings().allowed_namespaces == ("a", "b")
