# backend/services/word_parser/app/main.py
import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from docx import Document

# This must be the same path used by the file_service
SHARED_VOLUME_PATH = "/var/uploads"


class ParseRequest(BaseModel):
    file_id: str = Field(..., description="The unique filename of the Word (.docx) file to parse.")


class ParseResponse(BaseModel):
    file_id: str
    extracted_text: str

app = FastAPI(
    title="Word Document Parsing Service",
    description="Extracts text content from .docx files.",
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

@app.post("/parse_word", response_model=ParseResponse, tags=["Parsing"])
async def parse_word_endpoint(request: ParseRequest):
    """
    Given a file_id, reads the corresponding .docx file and returns its text content.
    """
    file_path = os.path.join(SHARED_VOLUME_PATH, request.file_id)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_id}")

    try:
        document = Document(file_path)
        # Keep empty paragraphs out to reduce noisy output.
        full_text = [para.text for para in document.paragraphs if para.text]
        return ParseResponse(file_id=request.file_id, extracted_text="\n".join(full_text))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse Word file {request.file_id}: {e}")

@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Word Parser Service"}
