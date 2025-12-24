"""
Prompt Templates

Default prompt templates for meeting phases.
Used when YAML files are not available.
"""



class PromptTemplates:
    """
    Default prompt templates.
    
    These templates are used as fallbacks when external
    YAML configurations are not available.
    """
    
    # Anti-bias statement to include in analysis prompts
    ANTI_BIAS_STATEMENT = """**CRITICAL: Avoid Confirmation Bias**
- Your analysis must be OBJECTIVE
- Do NOT favor any particular direction
- Analyze BOTH directions (long AND short) with equal rigor
- If data suggests a different view, say so clearly
- Your job is to find truth, not to justify existing positions"""
    
    # Vote JSON template - uses placeholder to avoid direction bias
    VOTE_JSON_TEMPLATE = '''{
  "direction": "<your_vote>",
  "confidence": <0-100>,
  "leverage": <1-10>,
  "take_profit_percent": <1-20>,
  "stop_loss_percent": <0.5-10>,
  "reasoning": "<brief explanation>"
}'''
    
    @classmethod
    def get_analysis_prompt(cls, agent_type: str, symbol: str, position_hint: str) -> str:
        """Get analysis prompt for an agent type."""
        prompts = {
            "technical": f"""Analyze the current technical situation for {symbol}.

{position_hint}

{cls.ANTI_BIAS_STATEMENT}

**Required Analysis Steps**:
1. Get the current market price
2. Fetch 4-hour candlestick data (100 candles)
3. Calculate technical indicators (RSI, MACD, Bollinger Bands)

Provide **objective analysis**:
- Current price and 24h change
- Technical indicators interpretation
- Trend analysis and key levels
- Support for LONG and SHORT positions
- Your independent recommendation""",

            "macro": f"""Analyze the macro-economic environment affecting {symbol}.

{position_hint}

{cls.ANTI_BIAS_STATEMENT}

**Required Steps**:
1. Search for latest market news
2. Analyze institutional movements

Provide **objective analysis**:
- Market liquidity conditions
- Macro factors affecting price
- Support for LONG and SHORT positions
- Your independent judgment""",

            "sentiment": f"""Analyze market sentiment for {symbol}.

{position_hint}

{cls.ANTI_BIAS_STATEMENT}

**Required Steps**:
1. Get Fear & Greed Index
2. Get funding rate
3. Search for sentiment data

Provide **objective analysis**:
- Sentiment indicators
- Social media trends
- Support for LONG and SHORT positions
- Your independent judgment""",

            "quant": f"""Analyze quantitative signals for {symbol}.

{position_hint}

{cls.ANTI_BIAS_STATEMENT}

**Required Steps**:
1. Get price data
2. Calculate multi-timeframe indicators

Provide **objective analysis**:
- Volatility analysis
- Momentum signals
- Support for LONG and SHORT positions
- Your independent judgment"""
        }
        
        return prompts.get(agent_type.lower(), prompts.get("technical", ""))
    
    @classmethod
    def get_vote_prompt(cls, symbol: str, position_summary: str) -> str:
        """Get vote collection prompt."""
        return f"""Based on your analysis, provide your trading vote for {symbol}.

{position_summary}

**Output your vote as JSON:**
```json
{cls.VOTE_JSON_TEMPLATE}
```

**Direction Options** (choose ONE):
- "short" - Open/add short position (bearish)
- "long" - Open/add long position (bullish)
- "hold" - Wait, no action
- "close" - Close current position

**IMPORTANT**:
- Base your vote ONLY on your analysis
- Be specific about confidence (0-100)
- Consider risk/reward in your suggestions
- Provide clear reasoning"""
    
    @classmethod
    def get_leader_prompt(cls, meeting_context: str) -> str:
        """Get leader summary prompt."""
        return f"""You are the Roundtable Leader. Summarize the meeting and provide strategic guidance.

{meeting_context}

## Your Task

Provide a comprehensive meeting summary that:
1. Synthesizes all expert opinions
2. Highlights key agreements and disagreements
3. Identifies main factors driving consensus
4. Provides strategic recommendations
5. Notes important risks

**Format:**

### Meeting Summary
[Synthesize expert opinions]

### Key Findings
[Main analysis points]

### Consensus View
[Direction and rationale]

### Recommended Action
[What TradeExecutor should consider]

### Risk Factors
[Important risks to monitor]"""
