"""
Analysis V2 Compatibility Router.

This module is kept for backward compatibility with legacy imports.
Canonical implementation lives in `analysis.py`.
"""

from fastapi import APIRouter, Depends, Request

from ...models.analysis_models import AnalysisRequest
from ...core.auth import CurrentUser, get_current_user
from .analysis import (
    get_analysis_status_v2 as _get_analysis_status_v2,
    get_available_scenarios as _get_available_scenarios,
    start_analysis_v2 as _start_analysis_v2,
)

router = APIRouter()


@router.post("/start")
async def start_analysis_v2(
    request: AnalysisRequest,
    http_request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    return await _start_analysis_v2(request, http_request, current_user)


@router.get("/{session_id}/status")
async def get_analysis_status_v2(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    return await _get_analysis_status_v2(session_id, current_user)


@router.get("/scenarios")
async def get_available_scenarios():
    return await _get_available_scenarios()
