"""Streaming diagnostic API."""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.agent.workflow import DiagnosticWorkflow
from app.api.auth import require_token
from app.config import settings
from app.schemas import DiagnoseRequest

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)
request_slots = asyncio.Semaphore(settings.max_concurrent)
request_times: dict[str, deque[float]] = defaultdict(deque)


def _event(name: str, payload: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n"


@router.post("/diagnose")
async def diagnose(request: DiagnoseRequest, token: str = Depends(require_token)) -> StreamingResponse:
    if request.namespace not in settings.allowed_namespaces:
        raise HTTPException(status_code=403, detail="namespace is not allowed")
    now = time.monotonic()
    history = request_times[token]
    while history and now - history[0] > 60:
        history.popleft()
    if len(history) >= settings.rate_limit:
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    history.append(now)
    request_id = str(uuid4())

    async def stream():
        logger.info("diagnosis_started request_id=%s namespace=%s", request_id, request.namespace)
        yield _event("status", {"request_id": request_id, "message": "Collecting evidence"})
        try:
            async with request_slots:
                result = await asyncio.wait_for(
                    DiagnosticWorkflow().run(request_id, request), timeout=settings.request_timeout
                )
            for item in result.evidence:
                yield _event("tool_result", item.model_dump())
            yield _event("completed", result.model_dump())
        except asyncio.CancelledError:
            logger.info("diagnosis_cancelled request_id=%s", request_id)
            raise
        except asyncio.TimeoutError:
            logger.warning("diagnosis_timeout request_id=%s", request_id)
            yield _event("error", {"request_id": request_id, "message": "diagnosis timed out"})
        except Exception as exc:
            logger.exception("diagnosis_failed request_id=%s", request_id)
            yield _event("error", {"request_id": request_id, "message": str(exc)})

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Request-ID": request_id})
