"""Environment-backed application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

DEFAULT_TOKEN = "dev-token"


def _list(name: str, default: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in os.getenv(name, default).split(",") if item.strip())


def _bool(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class Settings:
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    bearer_token: str = field(default_factory=lambda: os.getenv("API_BEARER_TOKEN", DEFAULT_TOKEN))
    allowed_namespaces: tuple[str, ...] = field(default_factory=lambda: _list("K8S_ALLOWED_NAMESPACES", "inferops-demo"))
    cors_origins: tuple[str, ...] = field(default_factory=lambda: _list("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"))
    kubectl_path: str = field(default_factory=lambda: os.getenv("KUBECTL_PATH", "kubectl"))
    max_tool_calls: int = field(default_factory=lambda: int(os.getenv("AGENT_MAX_TOOL_CALLS", "8")))
    tool_timeout: float = field(default_factory=lambda: float(os.getenv("TOOL_TIMEOUT_SECONDS", "10")))
    max_log_lines: int = field(default_factory=lambda: int(os.getenv("MAX_LOG_LINES", "60")))
    max_tool_output_bytes: int = field(default_factory=lambda: int(os.getenv("MAX_TOOL_OUTPUT_BYTES", "1000000")))
    demo_mode: bool = field(default_factory=lambda: _bool("DEMO_MODE", "true"))
    use_llm: bool = field(default_factory=lambda: _bool("USE_LLM", "false"))
    vllm_base_url: str = field(default_factory=lambda: os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1"))
    vllm_model: str = field(default_factory=lambda: os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-1.5B-Instruct"))
    llm_timeout: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "30")))
    embedding_backend: str = field(default_factory=lambda: os.getenv("EMBEDDING_BACKEND", "hash"))
    triton_http_url: str = field(default_factory=lambda: os.getenv("TRITON_HTTP_URL", "http://127.0.0.1:8002"))
    triton_model: str = field(default_factory=lambda: os.getenv("TRITON_MODEL_NAME", "embedding"))
    tokenizer_path: str = field(default_factory=lambda: os.getenv("EMBEDDING_TOKENIZER_PATH", "model_repository/embedding/tokenizer/tokenizer.json"))
    embedding_max_tokens: int = field(default_factory=lambda: int(os.getenv("EMBEDDING_MAX_TOKENS", "256")))
    use_qdrant: bool = field(default_factory=lambda: _bool("USE_QDRANT", "false"))
    qdrant_url: str = field(default_factory=lambda: os.getenv("QDRANT_URL", "http://127.0.0.1:6333"))
    qdrant_collection: str = field(default_factory=lambda: os.getenv("QDRANT_COLLECTION", "inferops_docs"))
    docs_index_path: str = field(default_factory=lambda: os.getenv("DOCS_INDEX_PATH", "data/docs-index.json"))
    docs_limit: int = field(default_factory=lambda: int(os.getenv("DOCS_LIMIT", "3")))
    request_timeout: float = field(default_factory=lambda: float(os.getenv("AGENT_TIMEOUT_SECONDS", "60")))
    max_concurrent: int = field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_REQUESTS", "4")))
    rate_limit: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "20")))

    def validate(self) -> None:
        """Fail at startup rather than serve with an unsafe or impossible configuration."""
        if self.app_env == "production" and self.bearer_token == DEFAULT_TOKEN:
            raise RuntimeError("API_BEARER_TOKEN must be changed from the development default in production")
        if len(self.bearer_token) < 8:
            raise RuntimeError("API_BEARER_TOKEN must be at least 8 characters")
        if self.embedding_backend not in {"hash", "triton"}:
            raise RuntimeError("EMBEDDING_BACKEND must be 'hash' or 'triton'")
        if not self.allowed_namespaces:
            raise RuntimeError("K8S_ALLOWED_NAMESPACES must list at least one namespace")


settings = Settings()
