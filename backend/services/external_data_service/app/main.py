# backend/services/external_data_service/app/main.py
import json
import os
from typing import Any, Dict

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


class CompanyInfoRequest(BaseModel):
    company_name: str | None = Field(default=None, description="The company name to search for.")
    ticker: str | None = Field(default=None, description="Backward-compatible ticker field.")


class CompanyInfoResponse(BaseModel):
    status: str  # 'found', 'not_found'
    data: Dict[str, Any] | None = None


app = FastAPI(
    title="External Data Service",
    description="Fetches private market company information from external APIs.",
    version="3.0.0",
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PoC safety: avoid returning fake company data unless explicitly enabled for local/dev.
ALLOW_MOCK_EXTERNAL_DATA = os.getenv("EXTERNAL_DATA_ALLOW_MOCK", "false").lower() == "true"


@app.post("/get_company_info", response_model=CompanyInfoResponse, tags=["Data Aggregation"])
async def get_company_info_endpoint(request: CompanyInfoRequest):
    query = (request.company_name or request.ticker or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="company_name (or ticker) is required")

    if not ALLOW_MOCK_EXTERNAL_DATA:
        raise HTTPException(
            status_code=501,
            detail="External data provider is not configured. Set up a real integration or enable EXTERNAL_DATA_ALLOW_MOCK for dev only.",
        )

    query_lower = query.lower()
    if "apple" in query_lower or "苹果" in query:
        return CompanyInfoResponse(
            status="found",
            data={
                "company_name": "苹果电脑贸易（上海）有限公司",
                "note": "MOCK DATA (dev-only)",
            },
        )

    return CompanyInfoResponse(status="not_found", data=None)


@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "External Data Service"}


@app.get("/network_test", tags=["Health Check"])
async def network_test():
    """Endpoint to test external network connectivity."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://www.google.com", timeout=10)
            return {"status": "success", "response_code": response.status_code}
    except httpx.RequestError as e:
        return {"status": "failed", "error": str(e)}
