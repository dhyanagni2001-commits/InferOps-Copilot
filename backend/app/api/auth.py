"""Bearer-token authentication for local and single-tenant deployments."""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Header, HTTPException, status

from app.config import settings


async def require_token(authorization: Optional[str] = Header(default=None)) -> str:
    # The token is injected from a Secret in Kubernetes and entered at runtime in the UI.
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(supplied.encode(), settings.bearer_token.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return supplied
