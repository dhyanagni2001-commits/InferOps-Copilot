"""Liveness, readiness, and public runtime configuration."""

from __future__ import annotations

import asyncio
import shutil
from typing import Any

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app import __version__
from app.config import settings
from app.retrieval.retriever import default_store

router = APIRouter()


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


async def _http_ok(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            return (await client.get(url)).status_code == 200
    except httpx.HTTPError:
        return False


@router.get("/health/ready")
async def ready() -> JSONResponse:
    """Required checks gate readiness; optional dependencies are reported but degrade gracefully."""
    checks: dict[str, Any] = {}
    required_ok = True
    if not settings.demo_mode:
        kubectl = shutil.which(settings.kubectl_path) is not None
        checks["kubectl"] = kubectl
        required_ok = kubectl

    try:
        checks["docs_index"] = await asyncio.to_thread(lambda: default_store().available())
    except Exception:
        checks["docs_index"] = False
    if settings.use_llm:
        base = settings.vllm_base_url.rstrip("/").removesuffix("/v1")
        checks["vllm"] = await _http_ok(f"{base}/health")
    if settings.embedding_backend == "triton":
        checks["triton"] = await _http_ok(f"{settings.triton_http_url.rstrip('/')}/v2/models/{settings.triton_model}/ready")

    body = {"status": "ready" if required_ok else "not_ready", "checks": checks}
    return JSONResponse(body, status_code=200 if required_ok else 503)


@router.get("/api/config")
async def runtime_config() -> dict[str, Any]:
    """Non-secret settings the UI uses to describe what the backend will do."""
    return {
        "version": __version__,
        "mode": "demo" if settings.demo_mode else "cluster",
        "allowed_namespaces": list(settings.allowed_namespaces),
        "llm_enabled": settings.use_llm,
        "llm_model": settings.vllm_model if settings.use_llm else None,
        "embedding_backend": settings.embedding_backend,
        "vector_store": "qdrant" if settings.use_qdrant else "local",
    }
