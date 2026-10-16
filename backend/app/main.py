"""InferOps Copilot API entry point."""

import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app import __version__
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.config import settings
from app.log_format import configure_logging

settings.validate()
configure_logging(settings.log_level)
logger = logging.getLogger("app.access")

app = FastAPI(title="InferOps Copilot", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def access_log(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    if not request.url.path.startswith(("/health", "/metrics")):
        logger.info("http_request", extra={
            "method": request.method, "path": request.url.path, "status": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            "request_id": response.headers.get("X-Request-ID", str(uuid4())),
        })
    return response


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(health_router)
app.include_router(chat_router)
