# backend/services/web_search_service/app/main.py
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from tavily import TavilyClient
from typing import List, Dict, Any, Optional

# --- Pydantic Models ---
class SearchRequest(BaseModel):
    query: str = Field(..., description="The search query.")
    max_results: int = Field(default=5, description="The maximum number of search results to return.")
    # Time filtering options
    topic: str = Field(default="general", description="Search topic: 'general' or 'news'. News topic enables days parameter.")
    time_range: str = Field(default=None, description="Time range: 'day', 'week', 'month', 'year' or None for no filter.")
    days: int = Field(default=None, description="Number of days back (only works with topic='news').")
    include_date: bool = Field(default=True, description="Whether to include published_date in results.")

class SearchResult(BaseModel):
    title: str
    url: str
    content: str
    score: float
    published_date: Optional[str] = Field(default=None, description="Published date of the content if available.")

class SearchResponse(BaseModel):
    results: List[SearchResult]

# --- FastAPI Application ---
app = FastAPI(
    title="Web Search Service",
    description="Provides real-time web search capabilities using the Tavily API.",
    version="3.0.0"
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Tavily Client ---
tavily_client = None

@app.on_event("startup")
def startup_event():
    global tavily_client
    try:
        # It's recommended to set the API key as an environment variable
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set.")
        tavily_client = TavilyClient(api_key=tavily_api_key)
        print("Successfully initialized Tavily client.")
    except Exception as e:
        print(f"Failed to initialize Tavily client: {e}")
        tavily_client = None

# --- Helper Functions ---
def fix_encoding(text: str) -> str:
    """
    Fixes common encoding issues (mojibake) where UTF-8 bytes were decoded as Latin-1.
    Example: "äººæ°‘" -> "人民"
    """
    if not text:
        return ""
    try:
        # Attempt to encode as Latin-1 (reversing the incorrect decode) and then decode as UTF-8.
        # This fixes cases where requests/tavily defaulted to ISO-8859-1 for UTF-8 content.
        return text.encode('latin-1').decode('utf-8')
    except Exception:
        # If it fails (e.g. characters not in Latin-1, or not valid UTF-8 bytes), return original
        return text

# --- API Endpoints ---
@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search_endpoint(request: SearchRequest):
    if not tavily_client:
        raise HTTPException(status_code=503, detail="Tavily client is not available.")

    try:
        # Build search parameters
        search_params = {
            "query": request.query,
            "search_depth": "advanced",  # Use advanced for more thorough results
            "max_results": request.max_results,
            "include_answer": False,
        }

        # Add topic parameter (general or news)
        if request.topic in ["general", "news"]:
            search_params["topic"] = request.topic

        # Add time_range parameter if provided
        if request.time_range and request.time_range in ["day", "week", "month", "year", "d", "w", "m", "y"]:
            search_params["time_range"] = request.time_range

        # Add days parameter (only works with topic="news")
        if request.days and request.topic == "news":
            search_params["days"] = request.days

        print(f"[WebSearch] Searching with params: {search_params}", flush=True)

        # Perform the search
        response = tavily_client.search(**search_params)

        # Format the response with published_date
        results = []
        for res in response.get("results", []):
            # Try to get published_date from the result
            published_date = res.get("published_date", None)

            results.append(SearchResult(
                title=fix_encoding(res.get("title", "")),
                url=res.get("url", ""),
                content=fix_encoding(res.get("content", "")),
                score=res.get("score", 0.0),
                published_date=published_date
            ))

        # Sort results by date if available (newest first)
        results_with_date = [r for r in results if r.published_date]
        results_without_date = [r for r in results if not r.published_date]

        # Sort by date descending
        results_with_date.sort(key=lambda x: x.published_date or "", reverse=True)

        # Put dated results first, then undated
        sorted_results = results_with_date + results_without_date

        return SearchResponse(results=sorted_results)
    except Exception as e:
        print(f"[WebSearch] Error: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail=f"An error occurred during the search: {str(e)}")

@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Web Search Service"}


# ==================== MCP (Model Context Protocol) Interface ====================

class MCPToolRequest(BaseModel):
    """MCP标准工具请求"""
    query: str = Field(..., description="搜索查询")
    max_results: int = Field(default=3, description="最大结果数")
    topic: str = Field(default="general", description="主题: general 或 news")
    time_range: str = Field(default=None, description="时间范围: day, week, month, year")
    days: int = Field(default=None, description="天数(仅 topic=news)")


class MCPToolResponse(BaseModel):
    """MCP标准工具响应"""
    success: bool
    result: Dict[str, Any] = None
    error: str = None


@app.post("/mcp/tools/{tool_name}", response_model=MCPToolResponse, tags=["MCP"])
async def execute_mcp_tool(tool_name: str, params: Dict[str, Any]):
    """
    执行MCP工具 (MCP标准接口)

    这是统一的MCP接口,所有工具通过此端点调用
    """
    if not tavily_client:
        return MCPToolResponse(
            success=False,
            error="Tavily client is not available"
        )

    try:
        if tool_name == "search" or tool_name == "tavily_search":
            # 通用搜索 - 只传递非None参数
            search_params = {
                "query": params.get("query", ""),
                "max_results": params.get("max_results", 3),
                "topic": params.get("topic", "general"),
                "include_date": True
            }
            if params.get("time_range"):
                search_params["time_range"] = params["time_range"]
            if params.get("days"):
                search_params["days"] = params["days"]

            search_req = SearchRequest(**search_params)

            # 复用现有搜索逻辑
            search_response = await search_endpoint(search_req)

            # 格式化为MCP响应
            results = [
                {
                    "title": r.title,
                    "url": r.url,
                    "content": r.content,
                    "published_date": r.published_date
                }
                for r in search_response.results
            ]

            # 构建summary
            summary_parts = [f"找到 {len(results)} 条关于'{params.get('query')}'的搜索结果:\n"]
            for i, res in enumerate(results[:3], 1):
                date_info = f"\n   发布日期: {res['published_date']}" if res.get('published_date') else ""
                summary_parts.append(
                    f"\n{i}. {res['title']}{date_info}\n"
                    f"   来源: {res['url']}\n"
                    f"   内容: {res['content'][:200]}..."
                )

            return MCPToolResponse(
                success=True,
                result={
                    "summary": "".join(summary_parts),
                    "results": results,
                    "query": params.get("query")
                }
            )

        elif tool_name == "news_search":
            # 新闻搜索 (强制 topic=news)
            search_params = {
                "query": params.get("query", ""),
                "max_results": params.get("max_results", 3),
                "topic": "news",
                "include_date": True
            }
            if params.get("time_range"):
                search_params["time_range"] = params.get("time_range", "week")

            search_req = SearchRequest(**search_params)

            search_response = await search_endpoint(search_req)

            results = [
                {
                    "title": r.title,
                    "url": r.url,
                    "content": r.content,
                    "published_date": r.published_date
                }
                for r in search_response.results
            ]

            summary = f"找到 {len(results)} 条最新新闻:\n"
            for i, res in enumerate(results[:3], 1):
                summary += f"{i}. {res['title']}\n   {res.get('published_date', 'N/A')}\n"

            return MCPToolResponse(
                success=True,
                result={
                    "summary": summary,
                    "results": results,
                    "query": params.get("query")
                }
            )

        else:
            return MCPToolResponse(
                success=False,
                error=f"Unknown tool: {tool_name}"
            )

    except Exception as e:
        print(f"[MCP] Tool execution error: {e}", flush=True)
        return MCPToolResponse(
            success=False,
            error=str(e)
        )


@app.get("/mcp/tools", tags=["MCP"])
async def list_mcp_tools():
    """
    列出可用的MCP工具
    """
    return {
        "tools": [
            {
                "name": "search",
                "description": "搜索互联网获取信息",
                "parameters": {
                    "query": {"type": "string", "required": True, "description": "搜索查询"},
                    "max_results": {"type": "integer", "default": 3, "description": "最大结果数"},
                    "topic": {"type": "string", "enum": ["general", "news"], "default": "general"},
                    "time_range": {"type": "string", "enum": ["day", "week", "month", "year"]},
                    "days": {"type": "integer", "description": "天数(仅 topic=news)"}
                }
            },
            {
                "name": "news_search",
                "description": "搜索最新新闻",
                "parameters": {
                    "query": {"type": "string", "required": True},
                    "max_results": {"type": "integer", "default": 3},
                    "time_range": {"type": "string", "default": "week"}
                }
            }
        ]
    }


@app.get("/health", tags=["Health Check"])
def health_check():
    """MCP标准健康检查"""
    return {
        "status": "ok" if tavily_client else "degraded",
        "service": "web-search-mcp",
        "version": "1.0.0"
    }
