# backend/services/external_data_service/app/main.py
import httpx
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any

class CompanyInfoRequest(BaseModel):
    company_name: str = Field(..., description="The company name to search for.")

class CompanyInfoResponse(BaseModel):
    status: str # 'found', 'not_found'
    data: Dict[str, Any] | None = None

app = FastAPI(
    title="External Data Service",
    description="Fetches private market company information from external APIs.",
    version="3.0.0" # V3 Upgrade
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Using a public API for searching Chinese company data as a demo substitute
# for paid services like Tianyancha or Qichacha.
EXTERNAL_API_URL = "https://www.tianyancha.com/cloud/cloud/search/company"

@app.post("/get_company_info", response_model=CompanyInfoResponse, tags=["Data Aggregation"])
async def get_company_info_endpoint(request: CompanyInfoRequest):
    """
    Given a company name, fetches its business registration information and financing history.
    """
    try:
        # This is a simplified example. A real implementation would require authentication
        # and more complex logic to handle the API response.
        # We are simulating a call to a service like Tianyancha.
        async with httpx.AsyncClient() as client:
            # Note: This public endpoint might be protected. In a real scenario,
            # we would use a proper, authenticated API endpoint.
            # For now, we will mock a successful response for a known company.
            if "apple" in request.company_name.lower() or "苹果" in request.company_name:
                mock_data = {
                    "company_name": "苹果电脑贸易（上海）有限公司",
                    "registration_status": "存续",
                    "legal_representative": "PETER RONALD DENWOOD",
                    "registered_capital": "6350万美元",
                    "founding_date": "2001-01-22",
                    "address": "上海市浦东新区自由贸易试验区马吉路88号",
                    "business_scope": "电子产品及配件的批发、进出口、佣金代理（拍卖除外）及相关配套服务。",
                    "financing_history": [
                        {"date": "1980-12-12", "round": "IPO", "investors": "Public"},
                        {"date": "1978-01-03", "round": "Venture", "investors": "Mike Markkula"}
                    ]
                }
                return CompanyInfoResponse(status='found', data=mock_data)
            else:
                 return CompanyInfoResponse(status='not_found', data=None)

    except Exception as e:
        import traceback
        print("====== DETAILED ERROR IN external_data_service ======")
        traceback.print_exc()
        print("=====================================================")
        raise HTTPException(status_code=500, detail=f"Failed to fetch external company data: {e}")


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

