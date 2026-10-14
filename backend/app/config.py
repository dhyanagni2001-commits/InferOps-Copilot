"""Environment-backed application settings."""

import os
from dataclasses import dataclass, field


def _namespaces() -> tuple[str, ...]:
    value = os.getenv("K8S_ALLOWED_NAMESPACES", "inferops-demo")
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    bearer_token: str = field(default_factory=lambda: os.getenv("API_BEARER_TOKEN", "dev-token"))
    allowed_namespaces: tuple[str, ...] = field(default_factory=_namespaces)
    max_tool_calls: int = field(default_factory=lambda: int(os.getenv("AGENT_MAX_TOOL_CALLS", "4")))
    tool_timeout: float = field(default_factory=lambda: float(os.getenv("TOOL_TIMEOUT_SECONDS", "10")))
    max_log_lines: int = field(default_factory=lambda: int(os.getenv("MAX_LOG_LINES", "200")))
    demo_mode: bool = field(default_factory=lambda: os.getenv("DEMO_MODE", "true").lower() == "true")
    use_llm: bool = field(default_factory=lambda: os.getenv("USE_LLM", "false").lower() == "true")
    vllm_base_url: str = field(default_factory=lambda: os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1"))
    vllm_model: str = field(default_factory=lambda: os.getenv("VLLM_MODEL", "local-model"))
    triton_http_url: str = field(default_factory=lambda: os.getenv("TRITON_HTTP_URL", "http://127.0.0.1:8002"))
    triton_model: str = field(default_factory=lambda: os.getenv("TRITON_MODEL_NAME", "embedding"))
    qdrant_url: str = field(default_factory=lambda: os.getenv("QDRANT_URL", "http://127.0.0.1:6333"))
    qdrant_collection: str = field(default_factory=lambda: os.getenv("QDRANT_COLLECTION", "inferops_docs"))
    use_qdrant: bool = field(default_factory=lambda: os.getenv("USE_QDRANT", "false").lower() == "true")
    docs_index_path: str = field(default_factory=lambda: os.getenv("DOCS_INDEX_PATH", "data/docs-index.json"))
    request_timeout: float = field(default_factory=lambda: float(os.getenv("AGENT_TIMEOUT_SECONDS", "60")))
    max_concurrent: int = field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_REQUESTS", "4")))
    rate_limit: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "20")))


settings = Settings()
