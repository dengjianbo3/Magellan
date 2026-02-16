"""
File Upload Router
文件上传路由

提供 BP、财务数据和公告文件上传功能
"""

import os
import logging
import tempfile
from typing import List

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
FILE_SERVICE_URL = os.getenv("FILE_SERVICE_URL", "http://file_service:8001")

MAX_UPLOAD_MB_HARD_CAP = int(os.getenv("REPORT_ORCH_UPLOAD_MAX_MB", "50"))


def _validate_extension(filename: str, allowed_extensions: List[str]) -> str:
    file_extension = os.path.splitext(filename or "")[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension}. Allowed: {', '.join(allowed_extensions)}",
        )
    return file_extension


def _spool_upload_to_tempfile(file: UploadFile, max_bytes: int) -> tuple[str, int]:
    """
    Stream-copy an UploadFile to a temp file while enforcing a hard size limit.
    Returns (temp_path, size_bytes).
    """
    total = 0
    chunk_size = 1024 * 1024  # 1MB
    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        while True:
            buf = file.file.read(chunk_size)
            if not buf:
                break
            total += len(buf)
            if total > max_bytes:
                raise HTTPException(status_code=413, detail=f"File too large. Max: {max_bytes} bytes")
            tmp.write(buf)
        tmp.flush()
        return tmp.name, total
    except Exception:
        try:
            tmp.close()
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
        raise
    finally:
        try:
            tmp.close()
        except Exception:
            pass


async def _forward_to_file_service(
    *,
    filename: str,
    content_type: str | None,
    temp_path: str,
) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        with open(temp_path, "rb") as f:
            files = {"file": (filename, f, content_type or "application/octet-stream")}
            response = await client.post(f"{FILE_SERVICE_URL}/upload", files=files)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {response.text}")
    return response.json()


@router.post("/upload_bp", tags=["File Upload"])
async def upload_bp_file(
    file: UploadFile = File(...),
    max_size_mb: int = 10
):
    """
    Upload BP (Business Plan) file to File Service.

    Supports: PDF, Word (.doc, .docx), Excel (.xls, .xlsx)

    Returns:
        file_id: Unique identifier for the uploaded file
        original_filename: Original name of the uploaded file
        file_size: Size of the file in bytes

    Usage:
        1. Frontend uploads BP file to this endpoint
        2. Get file_id from response
        3. Send file_id via WebSocket to start DD analysis
    """
    try:
        allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
        filename = file.filename or "upload"
        file_extension = _validate_extension(filename, allowed_extensions)

        effective_max_mb = max(1, min(int(max_size_mb), MAX_UPLOAD_MB_HARD_CAP))
        max_size_bytes = effective_max_mb * 1024 * 1024

        temp_path, file_size = _spool_upload_to_tempfile(file, max_size_bytes)
        try:
            upload_result = await _forward_to_file_service(
                filename=filename,
                content_type=file.content_type,
                temp_path=temp_path,
            )
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

        file_id = upload_result.get("file_id")

        logger.info(f"File uploaded: {filename} → {file_id} ({file_size} bytes)")

        return {
            "success": True,
            "file_id": file_id,
            "original_filename": filename,
            "file_size": file_size,
            "file_extension": file_extension,
            "message": "文件上传成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"文件上传失败: {str(e)}"
        )


@router.post("/v2/upload/bp", tags=["File Upload V2"])
async def upload_bp_v2(
    file: UploadFile = File(...),
    max_size_mb: int = 50
):
    """
    V2: Upload Business Plan file (simplified, local storage).

    Supports: PDF, Word (.doc, .docx), Excel (.xls, .xlsx)
    Max size: 50MB (configurable)

    Returns:
        file_id: Unique identifier for the uploaded file
        filename: Original filename
        size: File size in bytes
    """
    try:
        allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
        filename = file.filename or "upload"
        _validate_extension(filename, allowed_extensions)

        effective_max_mb = max(1, min(int(max_size_mb), MAX_UPLOAD_MB_HARD_CAP))
        max_size_bytes = effective_max_mb * 1024 * 1024

        temp_path, file_size = _spool_upload_to_tempfile(file, max_size_bytes)
        try:
            upload_result = await _forward_to_file_service(
                filename=filename,
                content_type=file.content_type,
                temp_path=temp_path,
            )
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

        file_id = upload_result.get("file_id")

        logger.info(f"BP file uploaded: {filename} → {file_id} ({file_size} bytes)")

        return {
            "success": True,
            "file_id": file_id,
            "filename": filename,
            "size": file_size
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BP upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/v2/upload/financial", tags=["File Upload V2"])
async def upload_financial_v2(
    file: UploadFile = File(...),
    max_size_mb: int = 50
):
    """
    V2: Upload Financial Data file (simplified, local storage).

    Supports: Excel (.xls, .xlsx), CSV
    Max size: 50MB (configurable)

    Returns:
        file_id: Unique identifier for the uploaded file
        filename: Original filename
        size: File size in bytes
    """
    try:
        allowed_extensions = ['.xls', '.xlsx', '.csv']
        filename = file.filename or "upload"
        _validate_extension(filename, allowed_extensions)

        effective_max_mb = max(1, min(int(max_size_mb), MAX_UPLOAD_MB_HARD_CAP))
        max_size_bytes = effective_max_mb * 1024 * 1024

        temp_path, file_size = _spool_upload_to_tempfile(file, max_size_bytes)
        try:
            upload_result = await _forward_to_file_service(
                filename=filename,
                content_type=file.content_type,
                temp_path=temp_path,
            )
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

        file_id = upload_result.get("file_id")

        logger.info(f"Financial file uploaded: {filename} → {file_id} ({file_size} bytes)")

        return {
            "success": True,
            "file_id": file_id,
            "filename": filename,
            "size": file_size
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Financial upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/v2/upload/filings", tags=["File Upload V2"])
async def upload_filings_v2(
    files: List[UploadFile] = File(...),
    max_size_mb: int = 50
):
    """
    V2: Upload Public Market Filings (simplified, local storage).

    Supports multiple files: PDF, Word (.doc, .docx)
    Max size per file: 50MB (configurable)

    Returns:
        file_ids: List of file IDs for uploaded files
        filenames: List of original filenames
        total_size: Total size of all files in bytes
    """
    try:
        allowed_extensions = ['.pdf', '.doc', '.docx']
        effective_max_mb = max(1, min(int(max_size_mb), MAX_UPLOAD_MB_HARD_CAP))
        max_size_bytes = effective_max_mb * 1024 * 1024

        file_ids = []
        filenames = []
        total_size = 0

        for file in files:
            filename = file.filename or "upload"
            _validate_extension(filename, allowed_extensions)

            temp_path, file_size = _spool_upload_to_tempfile(file, max_size_bytes)
            try:
                upload_result = await _forward_to_file_service(
                    filename=filename,
                    content_type=file.content_type,
                    temp_path=temp_path,
                )
            finally:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

            file_id = upload_result.get("file_id")
            file_ids.append(file_id)
            filenames.append(filename)
            total_size += file_size

            logger.info(f"Filing uploaded: {filename} → {file_id} ({file_size} bytes)")

        logger.info(f"Total {len(files)} filings uploaded, total size: {total_size} bytes")

        return {
            "success": True,
            "file_ids": file_ids,
            "filenames": filenames,
            "total_size": total_size,
            "count": len(files)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Filings upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
