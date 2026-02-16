# backend/services/file_service/app/main.py
import os
import json
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Shared volume path for file uploads
UPLOAD_DIRECTORY = "/var/uploads"
SHARED_VOLUME_PATH = UPLOAD_DIRECTORY  # Alias for compatibility

# PoC hardening defaults (override via env as needed)
MAX_UPLOAD_BYTES = int(os.getenv("FILE_SERVICE_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))  # 50MB

# Optional allow-list. Empty means allow any extension.
# Example: ".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt"
_ALLOWED_EXTENSIONS_RAW = (os.getenv("FILE_SERVICE_ALLOWED_EXTENSIONS") or "").strip()
ALLOWED_EXTENSIONS = {e.strip().lower() for e in _ALLOWED_EXTENSIONS_RAW.split(",") if e.strip()} if _ALLOWED_EXTENSIONS_RAW else set()

app = FastAPI(
    title="File Service",
    description="Handles file uploads and storage.",
    version="1.0.0"
)

def _parse_cors_allow_origins() -> list[str]:
    raw = (os.getenv("CORS_ALLOW_ORIGINS") or "http://localhost:5174,http://localhost:8081").strip()
    if not raw:
        return []
    if raw in ("*", "all"):
        return ["*"]
    if raw.startswith("["):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
        except Exception:
            pass
    return [o.strip() for o in raw.split(",") if o.strip()]

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Ensure the shared upload directory exists on startup."""
    os.makedirs(SHARED_VOLUME_PATH, exist_ok=True)

def _copyfileobj_limited(src, dst, max_bytes: int) -> int:
    total = 0
    chunk_size = 1024 * 1024  # 1MB
    while True:
        buf = src.read(chunk_size)
        if not buf:
            break
        total += len(buf)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail=f"File too large (max {max_bytes} bytes)")
        dst.write(buf)
    return total

@app.post("/upload", response_model=dict)
async def upload_file(file: UploadFile = File(...)):
    """
    Receives a file, saves it to the shared volume with a unique ID,
    and returns the generated file ID.
    """
    try:
        filename = file.filename or "upload"
        file_extension = os.path.splitext(filename)[1].lower()

        if ALLOWED_EXTENSIONS and file_extension and file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

        # Generate a unique filename to avoid collisions
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(SHARED_VOLUME_PATH, unique_filename)

        with open(file_path, "wb+") as file_object:
            size = _copyfileobj_limited(file.file, file_object, MAX_UPLOAD_BYTES)

        # The unique filename serves as the file_id
        return {"file_id": unique_filename, "original_filename": filename, "size": size}
    except HTTPException:
        try:
            if "file_path" in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        raise
    except Exception as e:
        try:
            if "file_path" in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "File Service"}
