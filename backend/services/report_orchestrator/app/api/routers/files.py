"""
File Upload Router
文件上传路由

This module guards multipart-based endpoints so the app can still import
in minimal dev/test environments where `python-multipart` isn't installed.
"""

from __future__ import annotations

import importlib.util

from fastapi import APIRouter, HTTPException


_MULTIPART_AVAILABLE = importlib.util.find_spec("multipart") is not None

if _MULTIPART_AVAILABLE:
    # Re-export the real router with UploadFile/File dependencies.
    from .files_multipart import router  # type: ignore[F401]
else:
    router = APIRouter()

    def _multipart_missing():
        raise HTTPException(
            status_code=503,
            detail='File/Form uploads require "python-multipart" to be installed (module "multipart").',
        )

    @router.post("/upload_bp", tags=["File Upload"])
    async def upload_bp_file_unavailable():
        return _multipart_missing()

    @router.post("/v2/upload/bp", tags=["File Upload V2"])
    async def upload_bp_v2_unavailable():
        return _multipart_missing()

    @router.post("/v2/upload/financial", tags=["File Upload V2"])
    async def upload_financial_v2_unavailable():
        return _multipart_missing()

    @router.post("/v2/upload/filings", tags=["File Upload V2"])
    async def upload_filings_v2_unavailable():
        return _multipart_missing()

