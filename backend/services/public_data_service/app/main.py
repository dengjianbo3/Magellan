# backend/services/public_data_service/app/main.py
import yfinance as yf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

class CompanyInfoRequest(BaseModel):
    # Using a stock ticker symbol is the most reliable way to fetch public data
    ticker: str = Field(..., description="The stock ticker symbol of the company (e.g., 'AAPL' for Apple).")

class CompanyInfoResponse(BaseModel):
    ticker: str
    company_name: str
    business_summary: str
    industry: str
    market_cap: float
    # We can add many more fields as needed
    # e.g., financial_data: dict

app = FastAPI(
    title="Public Data Aggregation Service",
    description="Fetches public company information using their stock ticker.",
    version="1.0.0"
)

@app.post("/get_company_info", response_model=CompanyInfoResponse, tags=["Data Aggregation"])
async def get_company_info_endpoint(request: CompanyInfoRequest):
    """
    Given a stock ticker, fetches public information about the company.
    """
    try:
        company = yf.Ticker(request.ticker)
        info = company.info

        if not info or 'shortName' not in info:
            raise HTTPException(status_code=404, detail=f"Could not find information for ticker: {request.ticker}")

        return CompanyInfoResponse(
            ticker=request.ticker,
            company_name=info.get('shortName', 'N/A'),
            business_summary=info.get('longBusinessSummary', 'N/A'),
            industry=info.get('industry', 'N/A'),
            market_cap=info.get('marketCap', 0.0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching data for {request.ticker}: {e}")

@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Public Data Service"}
