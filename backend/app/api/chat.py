"""Streaming diagnostic API."""

import json
import logging
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.agent.workflow import DiagnosticWorkflow
from app.api.auth import require_token
from app.config import settings
from app.schemas import DiagnoseRequest

router = APIRouter(prefix="/api", dependencies=[Depends(require_token)])
logger = logging.getLogger(__name__)


def _event(name: str, payload: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n"


@router.post("/diagnose")
async def diagnose(request: DiagnoseRequest) -> StreamingResponse:
    if request.namespace not in settings.allowed_namespaces:
        raise HTTPException(status_code=403, detail="namespace is not allowed")
    request_id = str(uuid4())

    async def stream():
        logger.info("diagnosis_started request_id=%s namespace=%s", request_id, request.namespace)
        yield _event("status", {"request_id": request_id, "message": "Collecting evidence"})
        try:
            result = await DiagnosticWorkflow().run(request_id, request)
            for item in result.evidence:
                yield _event("tool_result", item.model_dump())
            yield _event("completed", result.model_dump())
        except Exception as exc:
            logger.exception("diagnosis_failed request_id=%s", request_id)
            yield _event("error", {"request_id": request_id, "message": str(exc)})

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Request-ID": request_id})
