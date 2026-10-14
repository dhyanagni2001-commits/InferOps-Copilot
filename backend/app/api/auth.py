"""Simple bearer authentication suitable for local and demo deployments."""

from __future__ import annotations

import secrets
from typing import Optional
from fastapi import Header, HTTPException, status
from app.config import settings


async def require_token(authorization: Optional[str] = Header(default=None)) -> str:
    # Keep authentication explicit; production should inject the token as a Secret.
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not supplied or not secrets.compare_digest(supplied, settings.bearer_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token")
    return supplied
