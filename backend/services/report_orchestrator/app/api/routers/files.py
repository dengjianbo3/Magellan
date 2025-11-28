"""
File Upload Router
文件上传路由

提供 BP、财务数据和公告文件上传功能
"""

import os
import uuid
import logging
from typing import List

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
FILE_SERVICE_URL = os.getenv("FILE_SERVICE_URL", "http://file_service:8001")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
        # 1. Validate file type
        allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
        file_extension = os.path.splitext(file.filename)[1].lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_extension}. 支持的类型: {', '.join(allowed_extensions)}"
            )

        # 2. Read file content for size validation
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file size (convert MB to bytes)
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大: {file_size / (1024*1024):.2f}MB. 最大允许: {max_size_mb}MB"
            )

        # 3. Forward file to File Service
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Reset file pointer and create new UploadFile for forwarding
            files = {
                "file": (file.filename, file_content, file.content_type)
            }

            response = await client.post(
                f"{FILE_SERVICE_URL}/upload",
                files=files
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"文件上传失败: {response.text}"
                )

            # 4. Get file_id from File Service response
            upload_result = response.json()
            file_id = upload_result.get("file_id")

            logger.info(f"File uploaded: {file.filename} → {file_id} ({file_size} bytes)")

            return {
                "success": True,
                "file_id": file_id,
                "original_filename": file.filename,
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
        # Validate file type
        allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
        file_extension = os.path.splitext(file.filename)[1].lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. Allowed: {', '.join(allowed_extensions)}"
            )

        # Read and validate file size
        file_content = await file.read()
        file_size = len(file_content)
        max_size_bytes = max_size_mb * 1024 * 1024

        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {file_size / (1024*1024):.2f}MB. Max: {max_size_mb}MB"
            )

        # Generate unique file_id
        file_id = f"bp_{uuid.uuid4().hex[:12]}"
        safe_filename = f"{file_id}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"BP file saved: {file.filename} → {file_id} ({file_size} bytes)")

        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
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
        # Validate file type
        allowed_extensions = ['.xls', '.xlsx', '.csv']
        file_extension = os.path.splitext(file.filename)[1].lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. Allowed: {', '.join(allowed_extensions)}"
            )

        # Read and validate file size
        file_content = await file.read()
        file_size = len(file_content)
        max_size_bytes = max_size_mb * 1024 * 1024

        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {file_size / (1024*1024):.2f}MB. Max: {max_size_mb}MB"
            )

        # Generate unique file_id
        file_id = f"fin_{uuid.uuid4().hex[:12]}"
        safe_filename = f"{file_id}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"Financial file saved: {file.filename} → {file_id} ({file_size} bytes)")

        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
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
        max_size_bytes = max_size_mb * 1024 * 1024

        file_ids = []
        filenames = []
        total_size = 0

        for file in files:
            # Validate file type
            file_extension = os.path.splitext(file.filename)[1].lower()

            if file_extension not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file_extension}. Allowed: {', '.join(allowed_extensions)}"
                )

            # Read and validate file size
            file_content = await file.read()
            file_size = len(file_content)

            if file_size > max_size_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large: {file.filename} ({file_size / (1024*1024):.2f}MB). Max: {max_size_mb}MB"
                )

            # Generate unique file_id
            file_id = f"fil_{uuid.uuid4().hex[:12]}"
            safe_filename = f"{file_id}{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, safe_filename)

            # Save file
            with open(file_path, "wb") as f:
                f.write(file_content)

            file_ids.append(file_id)
            filenames.append(file.filename)
            total_size += file_size

            logger.info(f"Filing saved: {file.filename} → {file_id} ({file_size} bytes)")

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
