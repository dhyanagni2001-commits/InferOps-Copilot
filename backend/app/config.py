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


settings = Settings()
