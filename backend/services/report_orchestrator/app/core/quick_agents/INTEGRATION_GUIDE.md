# Quick Agents Integration Guide

## Overview

This guide explains how to integrate the 16 quick judgment agents into your investment analysis workflow.

## Scenario-Based Agent Selection

### Scenario 1: Early Stage Investment (早期投资)

**Use Case**: Analyzing a Pre-A or Series A startup

**Required Agents**:
```python
from app.core.quick_agents import (
    TeamQuickAgent,
    MarketQuickAgent,
    RedFlagAgent
)

async def analyze_early_stage(company_data):
    """Quick judgment for early stage startups"""

    # 1. Team evaluation (most important for early stage)
    team_agent = TeamQuickAgent()
    team_result = await team_agent.analyze({
        "company_name": company_data["name"],
        "stage": company_data["stage"],
        "description": company_data["description"],
        "team_members": company_data.get("team", [])
    })

    # 2. Market opportunity check
    market_agent = MarketQuickAgent()
    market_result = await market_agent.analyze({
        "company_name": company_data["name"],
        "industry": company_data["industry"],
        "description": company_data["description"]
    })

    # 3. Red flag detection
    red_flag_agent = RedFlagAgent()
    red_flag_result = await red_flag_agent.analyze({
        "company_name": company_data["name"]
    })

    # Calculate overall score
    overall_score = (
        team_result["score"] * 0.5 +      # Team is 50% weight
        market_result["score"] * 0.3 +    # Market is 30% weight
        red_flag_result["score"] * 0.2    # Red flags is 20% weight
    )

    return {
        "overall_score": overall_score,
        "recommendation": "PASS" if overall_score >= 0.7 else "REJECT",
        "team": team_result,
        "market": market_result,
        "red_flags": red_flag_result
    }
```

---

### Scenario 2: Growth Stage Investment (成长期投资)

**Use Case**: Analyzing a Series B/C company with revenue

**Required Agents**:
```python
from app.core.quick_agents import (
    FinancialHealthAgent,
    GrowthPotentialAgent,
    MarketPositionAgent
)

async def analyze_growth_stage(company_data):
    """Quick judgment for growth stage companies"""

    # 1. Financial health check
    financial_agent = FinancialHealthAgent()
    financial_result = await financial_agent.analyze({
        "company_name": company_data["name"],
        "stage": company_data["stage"],
        "annual_revenue": company_data.get("revenue"),
        "growth_rate": company_data.get("growth_rate")
    })

    # 2. Growth potential assessment
    growth_agent = GrowthPotentialAgent()
    growth_result = await growth_agent.analyze({
        "company_name": company_data["name"],
        "industry": company_data["industry"],
        "description": company_data["description"]
    })

    # 3. Market position evaluation
    position_agent = MarketPositionAgent()
    position_result = await position_agent.analyze({
        "company_name": company_data["name"],
        "industry": company_data["industry"],
        "competitors": company_data.get("competitors", [])
    })

    overall_score = (
        financial_result["score"] * 0.4 +
        growth_result["score"] * 0.35 +
        position_result["score"] * 0.25
    )

    return {
        "overall_score": overall_score,
        "recommendation": "PASS" if overall_score >= 0.65 else "REJECT",
        "financial": financial_result,
        "growth": growth_result,
        "market_position": position_result
    }
```

---

### Scenario 3: Public Market Investment (公开市场投资)

**Use Case**: Quick screening of public stocks

**Required Agents**:
```python
from app.core.quick_agents import (
    ValuationQuickAgent,
    FundamentalsAgent,
    TechnicalAnalysisAgent
)

async def analyze_public_stock(stock_data):
    """Quick judgment for public market stocks"""

    # 1. Valuation check
    valuation_agent = ValuationQuickAgent()
    valuation_result = await valuation_agent.analyze({
        "ticker": stock_data["ticker"],
        "company_name": stock_data["name"],
        "current_price": stock_data.get("price")
    })

    # 2. Fundamentals analysis
    fundamentals_agent = FundamentalsAgent()
    fundamentals_result = await fundamentals_agent.analyze({
        "ticker": stock_data["ticker"],
        "company_name": stock_data["name"],
        "industry": stock_data.get("industry")
    })

    # 3. Technical analysis
    technical_agent = TechnicalAnalysisAgent()
    technical_result = await technical_agent.analyze({
        "ticker": stock_data["ticker"],
        "company_name": stock_data["name"],
        "current_price": stock_data.get("price")
    })

    overall_score = (
        valuation_result["score"] * 0.35 +
        fundamentals_result["score"] * 0.45 +
        technical_result["score"] * 0.20
    )

    # Consider valuation level
    if valuation_result.get("valuation_level") == "high":
        overall_score *= 0.9  # Penalty for high valuation
    elif valuation_result.get("valuation_level") == "low":
        overall_score *= 1.1  # Bonus for low valuation

    return {
        "overall_score": min(overall_score, 1.0),
        "recommendation": "BUY" if overall_score >= 0.70 else "HOLD" if overall_score >= 0.50 else "SELL",
        "valuation": valuation_result,
        "fundamentals": fundamentals_result,
        "technical": technical_result
    }
```

---

### Scenario 4: Alternative Investment (另类投资 - Web3/Crypto)

**Use Case**: Evaluating cryptocurrency or Web3 projects

**Required Agents**:
```python
from app.core.quick_agents import (
    TechFoundationAgent,
    TokenomicsAgent,
    CommunityActivityAgent
)

async def analyze_web3_project(project_data):
    """Quick judgment for Web3/crypto projects"""

    # 1. Technology foundation
    tech_agent = TechFoundationAgent()
    tech_result = await tech_agent.analyze({
        "project_name": project_data["name"],
        "symbol": project_data["symbol"],
        "blockchain": project_data.get("blockchain"),
        "description": project_data["description"]
    })

    # 2. Tokenomics evaluation
    tokenomics_agent = TokenomicsAgent()
    tokenomics_result = await tokenomics_agent.analyze({
        "project_name": project_data["name"],
        "symbol": project_data["symbol"],
        "total_supply": project_data.get("total_supply"),
        "market_cap": project_data.get("market_cap")
    })

    # 3. Community activity
    community_agent = CommunityActivityAgent()
    community_result = await community_agent.analyze({
        "project_name": project_data["name"],
        "symbol": project_data["symbol"],
        "twitter_handle": project_data.get("twitter")
    })

    overall_score = (
        tech_result["score"] * 0.40 +        # Tech is critical
        tokenomics_result["score"] * 0.35 +  # Economics matters
        community_result["score"] * 0.25     # Community shows traction
    )

    return {
        "overall_score": overall_score,
        "recommendation": "INVEST" if overall_score >= 0.75 else "PASS",
        "technology": tech_result,
        "tokenomics": tokenomics_result,
        "community": community_result
    }
```

---

### Scenario 5: Industry Research (行业研究)

**Use Case**: Comprehensive industry landscape analysis

**Required Agents**:
```python
from app.core.quick_agents import (
    MarketSizeAgent,
    CompetitionLandscapeAgent,
    TrendAnalysisAgent,
    OpportunityScanAgent
)

async def analyze_industry(industry_data):
    """Industry research and opportunity identification"""

    # 1. Market size evaluation
    market_size_agent = MarketSizeAgent()
    market_size_result = await market_size_agent.analyze({
        "industry_name": industry_data["name"],
        "region": industry_data.get("region", "中国"),
        "year": industry_data.get("year", "2024")
    })

    # 2. Competition landscape
    competition_agent = CompetitionLandscapeAgent()
    competition_result = await competition_agent.analyze({
        "industry_name": industry_data["name"],
        "region": industry_data.get("region", "中国")
    })

    # 3. Trend analysis
    trend_agent = TrendAnalysisAgent()
    trend_result = await trend_agent.analyze({
        "industry_name": industry_data["name"],
        "time_horizon": industry_data.get("time_horizon", "中长期")
    })

    # 4. Opportunity scanning
    opportunity_agent = OpportunityScanAgent()
    opportunity_result = await opportunity_agent.analyze({
        "industry_name": industry_data["name"],
        "investment_stage": industry_data.get("stage_preference")
    })

    overall_score = (
        market_size_result["score"] * 0.30 +
        competition_result["score"] * 0.25 +
        trend_result["score"] * 0.25 +
        opportunity_result["score"] * 0.20
    )

    return {
        "overall_score": overall_score,
        "attractiveness": "HIGH" if overall_score >= 0.75 else "MEDIUM" if overall_score >= 0.55 else "LOW",
        "market_size": market_size_result,
        "competition": competition_result,
        "trends": trend_result,
        "opportunities": opportunity_result
    }
```

---

## Agent Configuration

### Default Configuration

All agents use the default web search service:
```python
agent = TeamQuickAgent()  # Uses http://web_search_service:8010
```

### Custom Configuration

Override the web search URL if needed:
```python
agent = TeamQuickAgent(
    web_search_url="http://custom-search-service:8000"
)
```

---

## Parallel Execution for Speed

For faster analysis, run agents in parallel:

```python
import asyncio

async def quick_analysis_parallel(company_data):
    """Run multiple agents in parallel"""

    # Create all agents
    team_agent = TeamQuickAgent()
    market_agent = MarketQuickAgent()
    red_flag_agent = RedFlagAgent()

    # Run all analyses in parallel
    team_task = team_agent.analyze({...})
    market_task = market_agent.analyze({...})
    red_flag_task = red_flag_agent.analyze({...})

    # Wait for all to complete
    team_result, market_result, red_flag_result = await asyncio.gather(
        team_task,
        market_task,
        red_flag_task
    )

    return {
        "team": team_result,
        "market": market_result,
        "red_flags": red_flag_result
    }
```

---

## Error Handling Best Practices

All agents handle errors gracefully, but you should still check results:

```python
async def safe_analysis(company_data):
    """Analysis with error checking"""

    try:
        team_agent = TeamQuickAgent()
        result = await team_agent.analyze(company_data)

        # Check if analysis was successful
        if result["score"] == 0.5 and "自动分析失败" in result.get("concerns", []):
            # Fallback: Manual review required
            return {
                "status": "manual_review_required",
                "result": result
            }

        return {
            "status": "success",
            "result": result
        }

    except Exception as e:
        # Handle unexpected errors
        return {
            "status": "error",
            "error": str(e),
            "result": None
        }
```

---

## Score Interpretation

### Individual Agent Scores
- **0.8-1.0**: Excellent - Strong positive signal
- **0.6-0.8**: Good - Generally positive
- **0.4-0.6**: Fair - Neutral, needs deeper review
- **0.2-0.4**: Poor - Negative signal
- **0.0-0.2**: Critical - Strong red flag

### Overall Scores (Weighted)
- **≥0.75**: Strong Pass/Buy - High confidence
- **0.65-0.75**: Pass/Buy - Good opportunity
- **0.50-0.65**: Hold/Review - Needs more analysis
- **0.35-0.50**: Reject/Avoid - Weak fundamentals
- **<0.35**: Strong Reject - Multiple issues

---

## Integration with State Machine

To integrate with the DD State Machine:

```python
# In dd_state_machine.py

async def quick_judgment_phase(self, scenario: str, target_data: dict):
    """Execute quick judgment based on scenario"""

    if scenario == "early_stage":
        result = await analyze_early_stage(target_data)
    elif scenario == "growth_stage":
        result = await analyze_growth_stage(target_data)
    elif scenario == "public_market":
        result = await analyze_public_stock(target_data)
    elif scenario == "alternative":
        result = await analyze_web3_project(target_data)
    elif scenario == "industry_research":
        result = await analyze_industry(target_data)
    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    # Decide next action based on result
    if result["overall_score"] >= 0.70:
        return "PROCEED_TO_DEEP_DIVE"
    elif result["overall_score"] >= 0.50:
        return "REQUEST_MORE_INFO"
    else:
        return "REJECT"
```

---

## Testing

Example test for an agent:

```python
import pytest
from app.core.quick_agents import TeamQuickAgent

@pytest.mark.asyncio
async def test_team_quick_agent():
    """Test team quick agent"""

    agent = TeamQuickAgent()

    result = await agent.analyze({
        "company_name": "测试公司",
        "stage": "Pre-A",
        "description": "AI创业公司",
        "team_members": ["张三", "李四"]
    })

    # Check result structure
    assert "score" in result
    assert "team_score" in result
    assert "highlights" in result
    assert "concerns" in result
    assert "summary" in result

    # Score should be between 0 and 1
    assert 0 <= result["score"] <= 1

    print(f"Team Score: {result['score']}")
    print(f"Summary: {result['summary']}")
```

---

## Next Steps

1. **Test each agent individually** with real data
2. **Tune the scoring weights** based on your investment philosophy
3. **Add custom agents** for specific industries or use cases
4. **Monitor agent performance** and iterate on prompts
5. **Build a feedback loop** to improve accuracy over time

---

## Support

For questions or issues:
- Check `AGENTS_OVERVIEW.md` for agent details
- Review individual agent files for implementation
- Refer to existing agents (TeamQuickAgent, FinancialHealthAgent) as templates
