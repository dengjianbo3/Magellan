"""
Context Compressor

Compresses tool results and agent outputs to minimize token usage.
Based on 2025 Context Engineering best practices from Anthropic and Manus AI.

Key strategies:
1. Full/Compact representation - store full data externally, keep compact in context
2. Extract key signals, discard noise
3. Structured output for downstream processing
"""

import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CompressedResult:
    """Compressed tool result with optional reference to full data"""
    tool_name: str
    summary: Dict[str, Any]
    full_data_ref: Optional[str] = None  # Reference ID if stored externally
    token_estimate: int = 0
    compressed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ToolResultCompressor:
    """
    Compress tool results to minimize context window usage.
    
    Compression strategies by tool type:
    - web_search: title + snippet (300 chars max)
    - get_kline: statistical summary only
    - get_fear_greed_index: single value + classification
    - generic: extract key fields, limit depth
    """
    
    # Maximum content length for different data types
    MAX_SNIPPET_LENGTH = 300
    MAX_SEARCH_RESULTS = 5
    MAX_LIST_ITEMS = 10
    MAX_NESTED_DEPTH = 2
    
    def __init__(self, file_memory=None):
        """
        Args:
            file_memory: Optional FileMemory instance for storing full data externally
        """
        self.file_memory = file_memory
        self._compression_stats = {
            "total_compressed": 0,
            "total_tokens_saved": 0
        }
    
    async def compress(self, tool_name: str, result: Any, store_full: bool = True) -> CompressedResult:
        """
        Compress a tool result.
        
        Args:
            tool_name: Name of the tool that produced this result
            result: Raw tool result
            store_full: Whether to store full data in file memory
            
        Returns:
            CompressedResult with summary and optional reference to full data
        """
        # Select compression strategy based on tool
        compressor = self._get_compressor(tool_name)
        summary = compressor(result)
        
        # Estimate token savings
        original_tokens = self._estimate_tokens(result)
        compressed_tokens = self._estimate_tokens(summary)
        
        # Store full data externally if configured
        full_data_ref = None
        if store_full and self.file_memory and original_tokens > 500:
            full_data_ref = await self.file_memory.write(
                key=f"tool:{tool_name}",
                content=result,
                metadata={"tool": tool_name, "compressed_at": datetime.now().isoformat()}
            )
        
        # Update stats
        self._compression_stats["total_compressed"] += 1
        self._compression_stats["total_tokens_saved"] += (original_tokens - compressed_tokens)
        
        logger.info(f"[ContextCompressor] {tool_name}: {original_tokens} → {compressed_tokens} tokens "
                   f"(saved {original_tokens - compressed_tokens})")
        
        return CompressedResult(
            tool_name=tool_name,
            summary=summary,
            full_data_ref=full_data_ref,
            token_estimate=compressed_tokens
        )
    
    def _get_compressor(self, tool_name: str):
        """Get compression function for tool type"""
        compressors = {
            "web_search": self._compress_search,
            "tavily_search": self._compress_search,
            "get_kline": self._compress_kline,
            "get_technical_indicators": self._compress_indicators,
            "get_fear_greed_index": self._compress_fear_greed,
            "get_defi_tvl": self._compress_tvl,
            "get_btc_price": self._compress_price,
            "get_market_data": self._compress_market_data,
        }
        return compressors.get(tool_name, self._compress_generic)
    
    def _compress_search(self, results: Any) -> Dict[str, Any]:
        """
        Compress web search results.
        
        Full article content → title + 300 char snippet
        """
        if not results:
            return {"results": [], "count": 0}
        
        # Handle different result formats
        if isinstance(results, dict):
            items = results.get("results", results.get("data", []))
        elif isinstance(results, list):
            items = results
        else:
            return {"raw": str(results)[:500]}
        
        compressed = []
        for item in items[:self.MAX_SEARCH_RESULTS]:
            if isinstance(item, dict):
                content = item.get("content", item.get("snippet", item.get("description", "")))
                compressed.append({
                    "title": item.get("title", "")[:100],
                    "url": item.get("url", item.get("link", ""))[:200],
                    "snippet": self._truncate(content, self.MAX_SNIPPET_LENGTH)
                })
            else:
                compressed.append({"text": self._truncate(str(item), self.MAX_SNIPPET_LENGTH)})
        
        return {
            "results": compressed,
            "count": len(items),
            "showing": len(compressed)
        }
    
    def _compress_kline(self, data: Any) -> Dict[str, Any]:
        """
        Compress K-line data to statistical summary.
        
        Raw OHLCV data → trend + key levels + volume info
        """
        if not data:
            return {"error": "no data"}
        
        if isinstance(data, dict):
            # Single candle or summary
            return {
                "period": data.get("period", "unknown"),
                "trend": "up" if data.get("close", 0) > data.get("open", 0) else "down",
                "change_pct": self._safe_pct_change(data.get("open"), data.get("close")),
                "high": data.get("high"),
                "low": data.get("low"),
                "close": data.get("close"),
                "volume_change": data.get("vol_change", 0)
            }
        
        if isinstance(data, list) and len(data) > 0:
            # Multiple candles - summarize
            closes = [c.get("close", c[-1] if isinstance(c, list) else 0) for c in data[-20:]]
            if closes:
                return {
                    "candles": len(data),
                    "latest_close": closes[-1] if closes else None,
                    "trend": "up" if closes[-1] > closes[0] else "down",
                    "high_20": max(closes),
                    "low_20": min(closes),
                    "change_20": self._safe_pct_change(closes[0], closes[-1])
                }
        
        return {"raw": str(data)[:300]}
    
    def _compress_indicators(self, data: Any) -> Dict[str, Any]:
        """Compress technical indicators to key signals only"""
        if not data:
            return {}
        
        if isinstance(data, dict):
            # Extract key indicator values
            compressed = {}
            key_indicators = ["rsi", "macd", "ma", "ema", "bb", "atr", "trend", "signal"]
            
            for key in key_indicators:
                for k, v in data.items():
                    if key in k.lower():
                        if isinstance(v, (int, float)):
                            compressed[k] = round(v, 2)
                        elif isinstance(v, str):
                            compressed[k] = v[:50]
            
            return compressed if compressed else {"summary": str(data)[:300]}
        
        return {"raw": str(data)[:300]}
    
    def _compress_fear_greed(self, data: Any) -> Dict[str, Any]:
        """Compress Fear & Greed Index to essentials"""
        if isinstance(data, dict):
            return {
                "value": data.get("value", data.get("index", data.get("fear_greed_index"))),
                "classification": data.get("classification", data.get("text", "")),
                "trend": data.get("trend", "stable")
            }
        return {"value": data}
    
    def _compress_tvl(self, data: Any) -> Dict[str, Any]:
        """Compress TVL data"""
        if isinstance(data, dict):
            return {
                "total_tvl": data.get("total_tvl", data.get("tvl")),
                "change_24h": data.get("change_24h", data.get("change")),
                "top_protocols": data.get("protocols", [])[:3]
            }
        return {"tvl": data}
    
    def _compress_price(self, data: Any) -> Dict[str, Any]:
        """Compress price data"""
        if isinstance(data, dict):
            return {
                "price": data.get("price", data.get("last")),
                "change_24h": data.get("change_24h", data.get("change")),
                "volume_24h": data.get("volume_24h", data.get("volume"))
            }
        return {"price": data}
    
    def _compress_market_data(self, data: Any) -> Dict[str, Any]:
        """Compress general market data"""
        if isinstance(data, dict):
            # Keep only essential fields
            essential = ["price", "volume", "change", "high", "low", "market_cap"]
            return {k: v for k, v in data.items() 
                    if any(key in k.lower() for key in essential)}
        return {"data": str(data)[:300]}
    
    def _compress_generic(self, data: Any, depth: int = 0) -> Any:
        """
        Generic compression for unknown data types.
        
        - Truncate strings
        - Limit list items
        - Limit nested depth
        """
        if depth > self.MAX_NESTED_DEPTH:
            return "..."
        
        if data is None:
            return None
        
        if isinstance(data, str):
            return self._truncate(data, 500)
        
        if isinstance(data, (int, float, bool)):
            return data
        
        if isinstance(data, list):
            return [self._compress_generic(item, depth + 1) 
                    for item in data[:self.MAX_LIST_ITEMS]]
        
        if isinstance(data, dict):
            return {k: self._compress_generic(v, depth + 1) 
                    for k, v in list(data.items())[:20]}
        
        return str(data)[:200]
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text with ellipsis"""
        if not text:
            return ""
        text = str(text)
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    def _safe_pct_change(self, old: Any, new: Any) -> Optional[float]:
        """Calculate percentage change safely"""
        try:
            old_f, new_f = float(old), float(new)
            if old_f == 0:
                return None
            return round(((new_f - old_f) / old_f) * 100, 2)
        except (TypeError, ValueError):
            return None
    
    def _estimate_tokens(self, data: Any) -> int:
        """Rough token estimation (1 token ≈ 4 chars)"""
        try:
            text = json.dumps(data, default=str)
            return len(text) // 4
        except (TypeError, ValueError):
            return len(str(data)) // 4
    
    def get_stats(self) -> Dict[str, int]:
        """Get compression statistics"""
        return self._compression_stats.copy()


class AnalysisSummarizer:
    """
    Summarize agent analysis to structured format.
    
    Converts verbose 500-800 token analysis into ~100 token structured summary.
    """
    
    SUMMARY_SCHEMA = {
        "direction": "long|short|hold",
        "confidence": "0-10",
        "key_signal": "one sentence core signal",
        "risk": "one sentence risk note",
        "data_points": ["key data 1", "key data 2"]
    }
    
    def __init__(self, llm_service=None):
        self.llm_service = llm_service
    
    async def summarize(self, agent_id: str, analysis: str) -> Dict[str, Any]:
        """
        Summarize a full analysis into structured format.
        
        Args:
            agent_id: The agent that produced the analysis
            analysis: Full analysis text
            
        Returns:
            Structured summary dict
        """
        if not analysis:
            return self._empty_summary(agent_id)
        
        # If LLM available, use it for intelligent summarization
        if self.llm_service:
            try:
                return await self._llm_summarize(agent_id, analysis)
            except Exception as e:
                logger.warning(f"LLM summarization failed: {e}, falling back to extraction")
        
        # Fallback: rule-based extraction
        return self._extract_summary(agent_id, analysis)
    
    async def _llm_summarize(self, agent_id: str, analysis: str) -> Dict[str, Any]:
        """Use LLM for intelligent summarization"""
        prompt = f"""Summarize this trading analysis into structured format.

ANALYSIS:
{analysis[:2000]}

OUTPUT JSON (no other text):
{{
    "direction": "long" or "short" or "hold",
    "confidence": 0-10 integer,
    "key_signal": "one sentence with the most important signal",
    "risk": "one sentence with the main risk",
    "data_points": ["key data point 1", "key data point 2"]
}}"""
        
        response = await self.llm_service.generate(
            prompt,
            model="gemini-2.0-flash",  # Use fast model
            temperature=0.1
        )
        
        # Parse JSON from response
        try:
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                summary = json.loads(response[start:end])
                summary["agent"] = agent_id
                return summary
        except json.JSONDecodeError:
            pass
        
        return self._extract_summary(agent_id, analysis)
    
    def _extract_summary(self, agent_id: str, analysis: str) -> Dict[str, Any]:
        """Rule-based summary extraction"""
        analysis_lower = analysis.lower()
        
        # Detect direction
        direction = "hold"
        if any(word in analysis_lower for word in ["bullish", "long", "buy", "upward", "看涨", "做多"]):
            direction = "long"
        elif any(word in analysis_lower for word in ["bearish", "short", "sell", "downward", "看跌", "做空"]):
            direction = "short"
        
        # Estimate confidence from language
        confidence = 5
        if any(word in analysis_lower for word in ["strong", "confident", "clear", "obvious", "确定", "明确"]):
            confidence = 8
        elif any(word in analysis_lower for word in ["weak", "uncertain", "unclear", "risky", "不确定"]):
            confidence = 3
        
        # Extract first meaningful sentence as key signal
        sentences = analysis.split(".")
        key_signal = sentences[0][:150] if sentences else "No signal"
        
        # Look for risk mentions
        risk = "Standard market risk"
        for sentence in sentences:
            if any(word in sentence.lower() for word in ["risk", "warning", "caution", "danger", "风险", "注意"]):
                risk = sentence[:100]
                break
        
        return {
            "agent": agent_id,
            "direction": direction,
            "confidence": confidence,
            "key_signal": key_signal,
            "risk": risk,
            "data_points": []
        }
    
    def _empty_summary(self, agent_id: str) -> Dict[str, Any]:
        """Return empty summary when no analysis available"""
        return {
            "agent": agent_id,
            "direction": "hold",
            "confidence": 0,
            "key_signal": "No analysis available",
            "risk": "Unknown",
            "data_points": []
        }


# Convenience function for quick compression
async def compress_tool_result(tool_name: str, result: Any) -> Dict[str, Any]:
    """Quick compress without external storage"""
    compressor = ToolResultCompressor()
    compressed = await compressor.compress(tool_name, result, store_full=False)
    return compressed.summary
