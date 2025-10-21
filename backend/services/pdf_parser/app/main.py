# backend/services/pdf_parser/app/main.py
import os
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import io

app = FastAPI(
    title="PDF Parsing Service",
    description="Extracts text content from PDF files.",
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

@app.post("/parse_pdf", response_model=ParseResponse, tags=["Parsing"])
async def parse_pdf_endpoint(request: ParseRequest):
    """
    Given a file_id, reads the corresponding PDF from the shared volume
    and returns its text content.
    """
    file_path = os.path.join(SHARED_VOLUME_PATH, request.file_id)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_id}")

    try:
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()

        if not text:
            # Handle cases where the PDF might be image-based (OCR needed in future)
            # For now, we'll consider it a successful parse with empty content.
            text = "PDF contained no extractable text. It might be an image-only document."

        return ParseResponse(file_id=request.file_id, extracted_text=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse PDF {request.file_id}: {e}")

@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "PDF Parser Service"}
