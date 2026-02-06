"""
Trigger Prompts - LLM Prompt Templates

Used by TriggerAgent for LLM analysis.
"""

TRIGGER_ANALYSIS_PROMPT = """You are a professional cryptocurrency market analyst. Your task is to determine whether the current market conditions require an immediate in-depth trading analysis.

## Current Market Data

### Latest News (past 1 hour)
{news_list}

### Technical Indicators
- BTC Current Price: ${current_price:,.2f}
- 15-minute Price Change: {price_change_15m}%
- 1-hour Price Change: {price_change_1h}%
- RSI (15-minute): {rsi_15m}
- MACD Crossover: {macd_crossover}
- Volume Spike: {volume_spike}
- Trend (15m/1h/4h): {trend_15m}/{trend_1h}/{trend_4h}

### Current Position
{position_info}

## Your Task

Analyze the above information and determine whether to **immediately** trigger an in-depth trading analysis.

Trigger conditions (reference, not exhaustive):
1. Major regulatory news (SEC, ETF, regulatory changes) - may cause significant price volatility
2. Exchange security incidents (hacks, asset freezes) - market panic
3. Macroeconomic events (Fed decisions, inflation data) - affects overall market sentiment
4. Dramatic technical changes (RSI extremes <25 or >75, strong MACD crossover, volume anomaly)
5. Rapid price movements (>2% in 15 minutes, or >3% in 1 hour)
6. Important statements (politicians, CEOs making significant crypto-related announcements)
7. Geopolitical events (wars, sanctions, etc. that may impact the market)
8. **Position Risk** - if holding a position and adverse market signals appear, be more sensitive to trigger analysis

Do NOT trigger for:
- Regular market analysis articles
- Minor price fluctuations (<1%)
- Technical indicators in normal range (RSI 30-70)
- No significant news events

## Output Format (must be valid JSON)

Please output ONLY in the following JSON format, no other content:
```json
{{
  "should_trigger": true or false,
  "urgency": "high" or "medium" or "low",
  "confidence": number from 0 to 100,
  "reasoning": "Your analysis reasoning, 2-3 sentences explaining why to trigger or not",
  "key_events": ["key event 1", "key event 2"]
}}
```

Output only JSON, nothing else."""


def build_trigger_prompt(news_items: list, ta_data: dict, position_data: dict = None) -> str:
    """Build trigger analysis prompt"""
    
    # Format news list
    if news_items:
        news_list = "\n".join([
            f"- [{item.get('source', 'Unknown')}] {item.get('title', '')}"
            for item in news_items[:10]  # Max 10 items
        ])
    else:
        news_list = "- No news fetched"
    
    # Format position info
    if position_data and position_data.get("has_position"):
        direction = position_data.get("direction", "none")
        pnl = position_data.get("pnl_percent", 0)
        size = position_data.get("size_usd", 0)
        pnl_status = "Profit" if pnl >= 0 else "Loss"
        position_info = f"""- Position Direction: {direction.upper()}
- Current PnL: {pnl_status} {abs(pnl):.2f}%
- Position Size: ${size:,.2f}
⚠️ Note: When holding a position, be more sensitive to adverse signals"""
    else:
        position_info = "- No current position"
    
    # Format technical indicators
    prompt = TRIGGER_ANALYSIS_PROMPT.format(
        news_list=news_list,
        current_price=ta_data.get('current_price', 0),
        price_change_15m=ta_data.get('price_change_15m', 0),
        price_change_1h=ta_data.get('price_change_1h', 0),
        rsi_15m=ta_data.get('rsi_15m', 50),
        macd_crossover="Yes" if ta_data.get('macd_crossover') else "No",
        volume_spike="Yes" if ta_data.get('volume_spike') else "No",
        trend_15m=ta_data.get('trend_15m', 'neutral'),
        trend_1h=ta_data.get('trend_1h', 'neutral'),
        trend_4h=ta_data.get('trend_4h', 'neutral'),
        position_info=position_info
    )
    
    return prompt
