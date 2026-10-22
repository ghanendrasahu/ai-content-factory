"""Shared FastAPI dependencies: auth for expensive job-spawn routes."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Header, HTTPException

from app.config import settings


def require_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    """Gate mutating POST routes when ``API_KEYS`` is configured.

    Empty ``API_KEYS`` keeps the local single-tenant workflow passing.
    """
    keys = [key for key in settings.API_KEYS if key]
    if not keys:
        return

    known = any(
        secrets.compare_digest((x_api_key or "").encode(), key.encode()) for key in keys
    )
    if not known:
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
