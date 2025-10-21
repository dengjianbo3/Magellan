# backend/services/public_data_service/app/main.py
import yfinance as yf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class CompanyInfoRequest(BaseModel):
    ticker: str = Field(..., description="The stock ticker or company name to search for.")

class CompanyOption(BaseModel):
    ticker: str
    name: str
    exchange: str

class CompanyInfoResponse(BaseModel):
    status: str # 'single_result', 'multiple_options', 'not_found'
    data: Dict[str, Any] | List[CompanyOption] | None = None

class FinancialSummaryResponse(BaseModel):
    years: List[int]
    revenues: List[float]
    profits: List[float]

app = FastAPI(
    title="Public Data Aggregation Service",
    description="Fetches public company information using their stock ticker.",
    version="2.1.0"
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/get_company_info", response_model=CompanyInfoResponse, tags=["Data Aggregation"])
async def get_company_info_endpoint(request: CompanyInfoRequest):
    """
    Given a stock ticker, fetches public information.
    If the ticker is ambiguous (like 'Apple'), it returns multiple options for disambiguation.
    """
    # --- SIMULATING AMBIGUITY FOR 'APPLE' ---
    if "APPLE" in request.ticker.upper():
        return CompanyInfoResponse(
            status='multiple_options',
            data=[
                CompanyOption(ticker='AAPL', name='Apple Inc.', exchange='NASDAQ'),
                CompanyOption(ticker='APLE', name='Apple Hospitality REIT', exchange='NYSE'),
            ]
        )

    try:
        company = yf.Ticker(request.ticker)
        info = company.info

        if not info or 'shortName' not in info:
            return CompanyInfoResponse(status='not_found', data=None)

        return CompanyInfoResponse(
            status='single_result',
            data={
                "ticker": request.ticker,
                "company_name": info.get('shortName', 'N/A'),
                "business_summary": info.get('longBusinessSummary', 'N/A'),
                "industry": info.get('industry', 'N/A'),
                "market_cap": info.get('marketCap', 0.0)
            }
        )
    except Exception:
        # Catch any exception from yfinance (e.g., ticker not found) and treat it as 'not_found'
        return CompanyInfoResponse(status='not_found', data=None)

@app.post("/get_financial_summary", response_model=FinancialSummaryResponse, tags=["Data Aggregation"])
async def get_financial_summary_endpoint(request: CompanyInfoRequest):
    """
    Given a stock ticker, fetches the last 4 years of financial summary (revenue and profit).
    """
    try:
        company = yf.Ticker(request.ticker)
        income_stmt = company.financials
        
        if income_stmt.empty:
            raise HTTPException(status_code=404, detail="Financial data not found for ticker.")

        # Get the last 4 available years, which are the columns
        years_columns = income_stmt.columns[:4]
        
        # Extract Total Revenue and Net Income, handling potential KeyError
        revenues = income_stmt.loc['Total Revenue'][years_columns].tolist() if 'Total Revenue' in income_stmt.index else []
        profits = income_stmt.loc['Net Income'][years_columns].tolist() if 'Net Income' in income_stmt.index else []

        if not revenues or not profits:
            raise HTTPException(status_code=404, detail="Could not extract revenue or profit data.")

        return FinancialSummaryResponse(
            years=[year.year for year in years_columns],
            revenues=[r / 1e6 for r in revenues], # Convert to millions
            profits=[p / 1e6 for p in profits] # Convert to millions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch or process financial data: {e}")


@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Public Data Service"}
