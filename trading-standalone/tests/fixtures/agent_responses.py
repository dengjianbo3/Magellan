"""
Agent Response Fixtures - 模拟Agent响应

提供各种场景下Agent的预定义响应，避免真实LLM调用。
"""

import pytest
from typing import Dict, List


# ==================== Technical Analyst 响应 ====================

@pytest.fixture
def technical_analyst_bullish():
    """技术分析师 - 看涨"""
    return """## 技术分析

我是**技术分析师「图表大师」**。

### 技术面评分: 8/10 (强烈看多)

**关键发现**:
1. **趋势**: 明确上升趋势，价格突破关键阻力位
2. **MA均线**: 短期均线金叉，多头排列
3. **MACD**: 快线上穿慢线，柱状图转正
4. **RSI**: 65，处于强势区但未超买
5. **成交量**: 放量上涨，资金积极入场

### 建议方向: 做多 (LONG)
**信心度**: 80%
**建议杠杆**: 7倍
**止盈**: 5%
**止损**: 2%
"""


@pytest.fixture
def technical_analyst_bearish():
    """技术分析师 - 看跌"""
    return """## 技术分析

我是**技术分析师「图表大师」**。

### 技术面评分: 3/10 (看空)

**关键发现**:
1. **趋势**: 下降趋势，价格跌破支撑位
2. **MA均线**: 短期均线死叉，空头排列
3. **MACD**: 快线下穿慢线，柱状图转负
4. **RSI**: 35，处于弱势区
5. **成交量**: 放量下跌，抛压严重

### 建议方向: 做空 (SHORT)
**信心度**: 75%
**建议杠杆**: 5倍
**止盈**: 5%
**止损**: 2%
"""


@pytest.fixture
def technical_analyst_neutral():
    """技术分析师 - 中性"""
    return """## 技术分析

我是**技术分析师「图表大师」**。

### 技术面评分: 5/10 (中性)

**关键发现**:
1. **趋势**: 横盘整理，方向不明
2. **MA均线**: 均线粘合，缠绕不清
3. **MACD**: 零轴附近震荡
4. **RSI**: 50，中性
5. **成交量**: 缩量，观望情绪浓厚

### 建议方向: 观望 (HOLD)
**信心度**: 40%
**理由**: 方向不明朗，等待突破
"""


# ==================== Macro Economist 响应 ====================

@pytest.fixture
def macro_economist_bullish():
    """宏观经济分析师 - 看涨"""
    return """## 宏观经济分析

我是**宏观经济分析师「全球视野」**。

### 宏观面评分: 7/10 (偏多)

**关键因素**:
1. **货币政策**: 美联储暂停加息，流动性改善
2. **通胀数据**: CPI回落，加密资产受益
3. **美元指数**: 美元走弱，风险资产反弹
4. **地缘政治**: 风险缓解，市场风险偏好提升

### 建议方向: 做多
**信心度**: 70%
**宏观支撑强劲**
"""


@pytest.fixture
def macro_economist_bearish():
    """宏观经济分析师 - 看跌"""
    return """## 宏观经济分析

我是**宏观经济分析师「全球视野」**。

### 宏观面评分: 3/10 (看空)

**关键因素**:
1. **货币政策**: 美联储鹰派，持续加息预期
2. **经济衰退**: 经济数据疲软，衰退风险上升
3. **美元指数**: 美元走强，压制风险资产
4. **监管政策**: 加密监管趋严

### 建议方向: 做空
**信心度**: 68%
**宏观环境不利**
"""


# ==================== Sentiment Analyst 响应 ====================

@pytest.fixture
def sentiment_analyst_bullish():
    """情绪分析师 - 乐观"""
    return """## 市场情绪分析

我是**情绪分析师「人心洞察」**。

### 情绪评分: 8/10 (极度乐观)

**情绪指标**:
1. **恐慌贪婪指数**: 75 (贪婪)
2. **社交媒体**: 积极情绪占比78%
3. **资金流向**: 大量资金流入
4. **持仓情况**: 多头持仓占比65%

### 建议方向: 做多
**信心度**: 82%
**市场情绪高涨**
"""


@pytest.fixture
def sentiment_analyst_bearish():
    """情绪分析师 - 恐慌"""
    return """## 市场情绪分析

我是**情绪分析师「人心洞察」**。

### 情绪评分: 2/10 (极度恐慌)

**情绪指标**:
1. **恐慌贪婪指数**: 25 (恐慌)
2. **社交媒体**: 消极情绪占比70%
3. **资金流向**: 持续流出
4. **持仓情况**: 空头持仓占比60%

### 建议方向: 做空
**信心度**: 73%
**市场恐慌蔓延**
"""


# ==================== Quant Strategist 响应 ====================

@pytest.fixture
def quant_strategist_bullish():
    """量化策略师 - 看涨"""
    return """## 量化分析

我是**量化策略师「数据猎手」**。

### 量化评分: 8/10 (强烈做多)

**量化信号**:
1. **动量因子**: +0.85 (强劲上涨动量)
2. **波动率**: 年化25%，处于正常区间
3. **资金费率**: +0.08%，多头强势
4. **套利空间**: 现货溢价，多头占优
5. **链上数据**: 活跃地址增加，资金流入

### 建议方向: 做多
**信心度**: 85%
**量化模型强烈看多**
"""


@pytest.fixture
def quant_strategist_bearish():
    """量化策略师 - 看跌"""
    return """## 量化分析

我是**量化策略师「数据猎手」**。

### 量化评分: 2/10 (强烈看空)

**量化信号**:
1. **动量因子**: -0.78 (强劲下跌动量)
2. **波动率**: 年化35%，剧烈波动
3. **资金费率**: -0.05%，空头强势
4. **套利空间**: 期货贴水，空头占优
5. **链上数据**: 活跃地址减少，资金外流

### 建议方向: 做空
**信心度**: 80%
**量化模型强烈看空**
"""


# ==================== Risk Assessor 响应 ====================

@pytest.fixture
def risk_assessor_conservative():
    """风险评估师 - 保守"""
    return """## 风险评估

我是**风险评估师「稳健守护」**。

### 风险评级: 中等

**风险提示**:
1. **市场风险**: 波动较大，需谨慎
2. **流动性风险**: 流动性充足
3. **系统性风险**: 宏观环境存在不确定性

### 风险管理建议:
- **建议杠杆**: 3-5倍（降低风险暴露）
- **止损**: 严格设置2%止损
- **仓位**: 不超过20%

**信心度**: 65%
"""


@pytest.fixture
def risk_assessor_aggressive():
    """风险评估师 - 激进"""
    return """## 风险评估

我是**风险评估师「稳健守护」**。

### 风险评级: 低

**风险分析**:
1. **市场风险**: 低，趋势明确
2. **流动性风险**: 充足
3. **系统性风险**: 可控

### 风险管理建议:
- **建议杠杆**: 7-10倍（可适度放大）
- **止损**: 2%
- **仓位**: 可到25-30%

**信心度**: 78%
**风险可控，可适度激进**
"""


# ==================== Leader 响应 ====================

@pytest.fixture
def leader_decision_long():
    """Leader - 决定做多"""
    return """## 主持人综合决策

综合各位专家意见，我得出以下结论：

### 专家共识:
- 技术面: 强烈看多 (80%)
- 宏观面: 偏多 (70%)
- 情绪面: 极度乐观 (82%)
- 量化面: 强烈看多 (85%)
- 风险评估: 风险可控 (78%)

### 最终决策:
专家高度一致看多，市场趋势明确，信心度高。

**综合信心度**: 79%
**决策**: 做多

[USE_TOOL: open_long(leverage="8", amount_usdt="2000", tp_percent="5.0", sl_percent="2.0")]
"""


@pytest.fixture
def leader_decision_short():
    """Leader - 决定做空"""
    return """## 主持人综合决策

综合各位专家意见，我得出以下结论：

### 专家共识:
- 技术面: 看空 (75%)
- 宏观面: 看空 (68%)
- 情绪面: 恐慌 (73%)
- 量化面: 强烈看空 (80%)
- 风险评估: 风险中等 (65%)

### 最终决策:
专家一致看空，建议做空。

**综合信心度**: 72%
**决策**: 做空

[USE_TOOL: open_short(leverage="6", amount_usdt="1800", tp_percent="5.0", sl_percent="2.0")]
"""


@pytest.fixture
def leader_decision_hold():
    """Leader - 决定观望"""
    return """## 主持人综合决策

综合各位专家意见，我得出以下结论：

### 专家共识:
- 技术面: 中性 (40%)
- 宏观面: 不确定 (50%)
- 情绪面: 观望 (45%)
- 量化面: 无明确信号 (48%)
- 风险评估: 风险偏高 (55%)

### 最终决策:
专家意见分歧较大，市场方向不明，建议观望。

**综合信心度**: 45%
**决策**: 观望

[USE_TOOL: hold(reason="市场方向不明朗，专家意见分歧，建议等待更明确信号")]
"""


@pytest.fixture
def leader_decision_add_long():
    """Leader - 决定追加多仓"""
    return """## 主持人综合决策

### 当前状态分析:
- 现有多仓盈利中
- 市场继续看多
- 可用资金充足

### 专家共识:
技术面和量化面继续强烈看多，建议追加仓位。

**综合信心度**: 76%
**决策**: 追加多仓

[USE_TOOL: open_long(leverage="7", amount_usdt="1500", tp_percent="6.0", sl_percent="2.0")]
"""


@pytest.fixture
def leader_decision_close_long():
    """Leader - 决定平掉多仓"""
    return """## 主持人综合决策

### 当前状态分析:
- 现有多仓
- 市场转向看空
- 建议及时止损

### 专家共识:
技术面和情绪面转空，建议平仓。

**综合信心度**: 70%
**决策**: 平仓

[USE_TOOL: hold(reason="市场方向改变，建议平掉当前多仓，技术面转弱")]
"""


# ==================== 组合场景 ====================

@pytest.fixture
def all_agents_bullish(
    technical_analyst_bullish,
    macro_economist_bullish,
    sentiment_analyst_bullish,
    quant_strategist_bullish,
    risk_assessor_aggressive
):
    """所有Agent都看涨"""
    return {
        "TechnicalAnalyst": technical_analyst_bullish,
        "MacroEconomist": macro_economist_bullish,
        "SentimentAnalyst": sentiment_analyst_bullish,
        "QuantStrategist": quant_strategist_bullish,
        "RiskAssessor": risk_assessor_aggressive,
    }


@pytest.fixture
def all_agents_bearish(
    technical_analyst_bearish,
    macro_economist_bearish,
    sentiment_analyst_bearish,
    quant_strategist_bearish,
    risk_assessor_conservative
):
    """所有Agent都看跌"""
    return {
        "TechnicalAnalyst": technical_analyst_bearish,
        "MacroEconomist": macro_economist_bearish,
        "SentimentAnalyst": sentiment_analyst_bearish,
        "QuantStrategist": quant_strategist_bearish,
        "RiskAssessor": risk_assessor_conservative,
    }


@pytest.fixture
def agents_mixed():
    """Agent意见混合 - 分歧较大"""
    return {
        "TechnicalAnalyst": technical_analyst_bullish,
        "MacroEconomist": macro_economist_bearish,
        "SentimentAnalyst": sentiment_analyst_neutral,
        "QuantStrategist": quant_strategist_bullish,
        "RiskAssessor": risk_assessor_conservative,
    }
