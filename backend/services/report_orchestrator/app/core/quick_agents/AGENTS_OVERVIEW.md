# Quick Agents Overview

## Agent Architecture

All quick agents follow a consistent pattern:

```python
class AgentName:
    def __init__(self, web_search_url: str)
    async def analyze(self, target: Dict[str, Any]) -> Dict[str, Any]
    async def _search_xxx(self, ...) -> list
    def _build_prompt(self, ...) -> str
    def _normalize_result(self, llm_result: Dict[str, Any]) -> Dict[str, Any]
```

## Agent Categories and Features

### 1. Early Stage Investment (早期投资)

#### TeamQuickAgent
- **Focus**: Founder background, team experience
- **Search**: "{company_name} 创始人 背景"
- **Returns**: team_score, highlights[], concerns[], summary

#### MarketQuickAgent
- **Focus**: Market size, growth potential, timing
- **Search**: "{company_name} {industry} 市场规模"
- **Returns**: score, market_size, growth_potential, concerns[], summary

#### RedFlagAgent
- **Focus**: Legal issues, financial risks, reputation
- **Search**: "{company_name} 风险 争议 诉讼"
- **Returns**: score, red_flags[], risk_level, summary

---

### 2. Growth Stage Investment (成长期投资)

#### FinancialHealthAgent
- **Focus**: Revenue, cash flow, profitability
- **Search**: "{company_name} 融资 收入 财务"
- **Returns**: score, revenue_assessment, cash_flow, profitability, concerns[], summary

#### GrowthPotentialAgent
- **Focus**: Growth drivers, scalability, sustainability
- **Search**: "{company_name} 增长 扩张 市场份额"
- **Returns**: score, growth_drivers[], scalability, sustainability, concerns[], summary

#### MarketPositionAgent
- **Focus**: Competitive advantage, market share, brand
- **Search**: "{company_name} 竞争对手 市场地位"
- **Returns**: score, competitive_advantage, market_share, brand_strength, barriers[], concerns[], summary

---

### 3. Public Market Investment (公开市场投资)

#### ValuationQuickAgent
- **Focus**: PE/PB ratio, relative/absolute valuation
- **Search**: "{ticker} PE PB 估值 价格目标"
- **Returns**: score, pe_ratio, pb_ratio, valuation_level, target_price, concerns[], summary

#### FundamentalsAgent
- **Focus**: Revenue growth, profit margin, ROE
- **Search**: "{ticker} 财报 业绩 营收 利润"
- **Returns**: score, revenue_growth, profit_margin, roe, financial_stability, concerns[], summary

#### TechnicalAnalysisAgent
- **Focus**: Price trend, support/resistance, momentum
- **Search**: "{ticker} 技术分析 股价走势"
- **Returns**: score, trend, support_level, resistance_level, momentum, volume_analysis, concerns[], summary

---

### 4. Alternative Investment (另类投资 - Web3/Crypto)

#### TechFoundationAgent
- **Focus**: Architecture, security audit, innovation
- **Search**: "{project_name} 技术 架构 审计 安全"
- **Returns**: score, architecture_quality, security_audit, innovation_level, code_quality, concerns[], summary

#### TokenomicsAgent
- **Focus**: Token distribution, inflation model, utility
- **Search**: "{symbol} tokenomics 代币分配 经济模型"
- **Returns**: score, distribution, inflation_model, utility, incentive_design, concerns[], summary

#### CommunityActivityAgent
- **Focus**: Social engagement, developer activity, holders
- **Search**: "{project_name} 社区 Twitter Discord GitHub"
- **Returns**: score, social_engagement, developer_activity, holder_count, community_quality, concerns[], summary

---

### 5. Industry Research (行业研究)

#### MarketSizeAgent
- **Focus**: TAM/SAM, growth rate, market maturity
- **Search**: "{industry_name} 市场规模 TAM 增长率"
- **Returns**: score, tam, sam, growth_rate, market_maturity, concerns[], summary

#### CompetitionLandscapeAgent
- **Focus**: Top players, market concentration, barriers
- **Search**: "{industry_name} 竞争格局 主要玩家"
- **Returns**: score, top_players[], market_concentration, entry_barriers, competitive_intensity, concerns[], summary

#### TrendAnalysisAgent
- **Focus**: Key trends, tech direction, policy support
- **Search**: "{industry_name} 趋势 技术路线 政策"
- **Returns**: score, key_trends[], tech_direction, policy_support, drivers[], barriers[], summary

#### OpportunityScanAgent
- **Focus**: Sub-sectors, innovations, investment timing
- **Search**: "{industry_name} 投资机会 细分赛道 创新"
- **Returns**: score, opportunities[], sub_sectors[], innovations[], timing_assessment, concerns[], summary

---

## Common Patterns

### Error Handling
All agents return safe default values when analysis fails:
```python
if "error" in llm_result:
    return {
        "score": 0.5,
        # ... other default fields
        "concerns": ["自动分析失败"],
        "summary": "评估未完成"
    }
```

### Score Range
All scores are normalized to 0-1 range where:
- 0.8-1.0: Excellent
- 0.6-0.8: Good
- 0.4-0.6: Fair
- 0.2-0.4: Poor
- 0.0-0.2: Critical issues

### LLM Integration
All agents use the shared `llm_helper`:
```python
from ..llm_helper import llm_helper

result = await llm_helper.call(prompt, response_format="json")
```

### Web Search Integration
All agents use the web_search_service:
```python
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.post(
        f"{self.web_search_url}/search",
        json={"query": query, "max_results": 3}
    )
```

## Usage Example

```python
from app.core.quick_agents import (
    TeamQuickAgent,
    GrowthPotentialAgent,
    ValuationQuickAgent,
    TechFoundationAgent,
    MarketSizeAgent
)

# Early stage startup analysis
team_agent = TeamQuickAgent()
result = await team_agent.analyze({
    "company_name": "AI Startup Inc",
    "stage": "Pre-A",
    "description": "AI-powered analytics platform",
    "team_members": ["John Doe", "Jane Smith"]
})

# Public market stock analysis
valuation_agent = ValuationQuickAgent()
result = await valuation_agent.analyze({
    "ticker": "AAPL",
    "company_name": "Apple Inc",
    "current_price": 175.50
})

# Web3 project analysis
tech_agent = TechFoundationAgent()
result = await tech_agent.analyze({
    "project_name": "Ethereum",
    "symbol": "ETH",
    "blockchain": "Ethereum",
    "description": "Decentralized platform for smart contracts"
})

# Industry research
market_agent = MarketSizeAgent()
result = await market_agent.analyze({
    "industry_name": "人工智能",
    "region": "中国",
    "year": "2024"
})
```

## File Structure

```
quick_agents/
├── __init__.py                      # Exports all agents
├── AGENTS_OVERVIEW.md              # This file
│
├── # Early Stage (3 agents)
├── team_quick_agent.py
├── market_quick_agent.py
├── red_flag_agent.py
│
├── # Growth Stage (3 agents)
├── financial_health_agent.py
├── growth_potential_agent.py
├── market_position_agent.py
│
├── # Public Market (3 agents)
├── valuation_quick_agent.py
├── fundamentals_agent.py
├── technical_analysis_agent.py
│
├── # Alternative Investment (3 agents)
├── tech_foundation_agent.py
├── tokenomics_agent.py
├── community_activity_agent.py
│
└── # Industry Research (4 agents)
    ├── market_size_agent.py
    ├── competition_landscape_agent.py
    ├── trend_analysis_agent.py
    └── opportunity_scan_agent.py
```

**Total: 16 Quick Agents**
