"""
Authentication helpers for report_orchestrator.

Uses auth_service `/api/auth/me` as the single source of truth for identity.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from typing import Any, Dict, Optional

import httpx
from fastapi import Header, HTTPException, Request, status
from pydantic import BaseModel


AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth_service:8007").rstrip("/")
AUTH_TIMEOUT_SECONDS = float(os.getenv("AUTH_TIMEOUT_SECONDS", "8"))
DEFAULT_USER_SCOPE = "default_user"
_CURRENT_USER_ID: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)
_CURRENT_ACCESS_TOKEN: ContextVar[Optional[str]] = ContextVar("current_access_token", default=None)


class CurrentUser(BaseModel):
    id: str
    email: Optional[str] = None
    role: Optional[str] = None
    name: Optional[str] = None
    organization: Optional[str] = None


def set_current_user_id(user_id: Optional[str]) -> None:
    _CURRENT_USER_ID.set((user_id or "").strip() or None)


def set_current_access_token(token: Optional[str]) -> None:
    _CURRENT_ACCESS_TOKEN.set((token or "").strip() or None)


def get_current_user_id(default: Optional[str] = None) -> str:
    user_id = (_CURRENT_USER_ID.get() or "").strip()
    if user_id:
        return user_id
    fallback = (default or DEFAULT_USER_SCOPE).strip()
    return fallback or DEFAULT_USER_SCOPE


def get_current_access_token() -> Optional[str]:
    token = (_CURRENT_ACCESS_TOKEN.get() or "").strip()
    return token or None


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )
    return parts[1].strip()


def extract_token_from_request(
    request: Request,
    authorization: Optional[str],
) -> Optional[str]:
    token = _extract_bearer_token(authorization)
    if token:
        return token
    # Fallback for image/file endpoints where headers are harder to set.
    query_token = (request.query_params.get("token") or "").strip()
    return query_token or None


async def resolve_user_from_token(token: str) -> CurrentUser:
    set_current_access_token(None)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    url = f"{AUTH_SERVICE_URL}/api/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(timeout=AUTH_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    data: Dict[str, Any] = response.json() if response.content else {}
    user_id = data.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user id missing",
        )
    user = CurrentUser.model_validate(data)
    set_current_user_id(user.id)
    set_current_access_token(token)
    return user


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(default=None),
) -> CurrentUser:
    set_current_access_token(None)
    token = extract_token_from_request(request, authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user = await resolve_user_from_token(token)
    set_current_user_id(user.id)
    return user
