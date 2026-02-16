# backend/services/excel_parser/app/main.py
import os
import json
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# This must be the same path used by the file_service
SHARED_VOLUME_PATH = "/var/uploads"

class ParseRequest(BaseModel):
    file_id: str = Field(..., description="The unique filename of the Excel file to parse.")

class ParseResponse(BaseModel):
    file_id: str
    extracted_data: dict[str, list[dict]] # A dict where keys are sheet names

app = FastAPI(
    title="Excel Parsing Service",
    description="Extracts content from Excel files into a structured format.",
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

@app.post("/parse_excel", response_model=ParseResponse, tags=["Parsing"])
async def parse_excel_endpoint(request: ParseRequest):
    """
    Given a file_id, reads the corresponding Excel file from the shared volume
    and returns its content as a structured JSON object.
    """
    file_path = os.path.join(SHARED_VOLUME_PATH, request.file_id)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_id}")

    try:
        xls = pd.ExcelFile(file_path)
        all_sheets_data = {}
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name)
            # Convert dataframe to a list of dictionaries for easy JSON serialization
            # orient='records' creates a list like [{col1: val1}, {col2: val2}, ...]
            sheet_data = df.to_dict(orient='records')
            all_sheets_data[sheet_name] = sheet_data

        return ParseResponse(file_id=request.file_id, extracted_data=all_sheets_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse Excel file {request.file_id}: {e}")

@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Excel Parser Service"}
