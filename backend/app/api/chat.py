"""Streaming diagnostic API (Server-Sent Events over POST)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.agent.workflow import DiagnosticWorkflow
from app.api.auth import require_token
from app.config import settings
from app.metrics import DIAGNOSIS_FAILURES
from app.schemas import DiagnoseRequest

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)
request_slots = asyncio.Semaphore(settings.max_concurrent)


class RateLimiter:
    """Sliding one-minute window per bearer token."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self.history: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        history = self.history[key]
        while history and now - history[0] > 60:
            history.popleft()
        if len(history) >= self.per_minute:
            return False
        history.append(now)
        return True


rate_limiter = RateLimiter(settings.rate_limit)


def sse(name: str, payload: dict[str, Any]) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, default=str)}\n\n"


async def _with_deadline(events: AsyncIterator[tuple[str, dict]], seconds: float) -> AsyncIterator[tuple[str, dict]]:
    deadline = time.monotonic() + seconds
    iterator = events.__aiter__()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise asyncio.TimeoutError
        try:
            yield await asyncio.wait_for(iterator.__anext__(), remaining)
        except StopAsyncIteration:
            return


@router.post("/diagnose")
async def diagnose(request: DiagnoseRequest, token: str = Depends(require_token)) -> StreamingResponse:
    if request.namespace not in settings.allowed_namespaces:
        raise HTTPException(status_code=403, detail=f"namespace '{request.namespace}' is not allowed")
    if not rate_limiter.allow(token):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    request_id = str(uuid4())

    async def stream() -> AsyncIterator[str]:
        logger.info("diagnosis_started", extra={
            "request_id": request_id, "namespace": request.namespace,
            "kind": request.workload.kind, "workload": request.workload.name,
        })
        try:
            if request_slots.locked():
                yield sse("status", {"request_id": request_id, "message": "Waiting for a free diagnostic slot"})
            async with request_slots:
                workflow = DiagnosticWorkflow().stream(request_id, request)
                async for name, payload in _with_deadline(workflow, settings.request_timeout):
                    yield sse(name, payload)
        except asyncio.CancelledError:
            DIAGNOSIS_FAILURES.labels(reason="cancelled").inc()
            logger.info("diagnosis_cancelled", extra={"request_id": request_id})
            raise
        except asyncio.TimeoutError:
            DIAGNOSIS_FAILURES.labels(reason="timeout").inc()
            logger.warning("diagnosis_timeout", extra={"request_id": request_id})
            yield sse("error", {"request_id": request_id, "message": f"diagnosis timed out after {settings.request_timeout:g}s"})
        except Exception:
            DIAGNOSIS_FAILURES.labels(reason="exception").inc()
            logger.exception("diagnosis_failed", extra={"request_id": request_id})
            yield sse("error", {"request_id": request_id, "message": "internal error; see server logs for request_id"})

    return StreamingResponse(
        stream(), media_type="text/event-stream",
        headers={"X-Request-ID": request_id, "Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
