# backend/services/word_parser/app/main.py
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from docx import Document
import io

app = FastAPI(
    title="Word Document Parsing Service",
    description="Extracts text content from .docx files.",
    version="1.0.0"
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        full_text = [para.text for para in document.paragraphs]
        return ParseResponse(file_id=request.file_id, extracted_text="\n".join(full_text))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse Word file {request.file_id}: {e}")

@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Word Parser Service"}
