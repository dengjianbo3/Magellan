"""
Trigger Prompts - LLM 提示词模板

用于 TriggerAgent 的 LLM 分析。
"""

TRIGGER_ANALYSIS_PROMPT = """你是一个专业的加密货币市场分析师。你的任务是判断当前市场状况是否需要立即进行深度交易分析。

## 当前市场数据

### 最新新闻 (过去1小时)
{news_list}

### 技术指标
- BTC 当前价格: ${current_price:,.2f}
- 15分钟价格变化: {price_change_15m}%
- 1小时价格变化: {price_change_1h}%
- RSI (15分钟): {rsi_15m}
- MACD 交叉: {macd_crossover}
- 成交量异常: {volume_spike}
- 趋势 (15m/1h/4h): {trend_15m}/{trend_1h}/{trend_4h}

## 你的任务

分析以上信息，判断是否需要**立即**触发深度交易分析。

触发条件参考 (但不限于):
1. 重大监管新闻 (SEC、ETF、法规变化) - 可能导致大幅价格波动
2. 交易所安全事件 (黑客攻击、资产冻结) - 市场恐慌
3. 宏观经济事件 (美联储决策、通胀数据) - 影响整体市场情绪
4. 技术面剧烈变化 (RSI极值<25或>75、MACD强交叉、成交量异常) 
5. 价格快速波动 (15分钟内变化>2%，或1小时内变化>3%)
6. 重要人物言论 (政要、CEO发表关于加密货币的重要声明)
7. 地缘政治事件 (战争、制裁等可能影响市场的事件)

不触发的情况:
- 普通的市场分析文章
- 价格小幅波动 (<1%)
- 技术指标在正常范围内 (RSI 30-70)
- 没有重大新闻事件

## 输出格式 (必须是有效的JSON)

请严格按照以下JSON格式输出，不要输出其他任何内容:
```json
{{
  "should_trigger": true或false,
  "urgency": "high"或"medium"或"low",
  "confidence": 0到100的数字,
  "reasoning": "你的分析理由，2-3句话说明为什么触发或不触发",
  "key_events": ["关键事件1", "关键事件2"]
}}
```

只输出JSON，不要其他内容。"""


def build_trigger_prompt(news_items: list, ta_data: dict) -> str:
    """构建触发器分析 Prompt"""
    
    # 格式化新闻列表
    if news_items:
        news_list = "\n".join([
            f"- [{item.get('source', 'Unknown')}] {item.get('title', '')}"
            for item in news_items[:10]  # 最多10条
        ])
    else:
        news_list = "- 没有获取到新闻"
    
    # 格式化技术指标
    prompt = TRIGGER_ANALYSIS_PROMPT.format(
        news_list=news_list,
        current_price=ta_data.get('current_price', 0),
        price_change_15m=ta_data.get('price_change_15m', 0),
        price_change_1h=ta_data.get('price_change_1h', 0),
        rsi_15m=ta_data.get('rsi_15m', 50),
        macd_crossover="是" if ta_data.get('macd_crossover') else "否",
        volume_spike="是" if ta_data.get('volume_spike') else "否",
        trend_15m=ta_data.get('trend_15m', 'neutral'),
        trend_1h=ta_data.get('trend_1h', 'neutral'),
        trend_4h=ta_data.get('trend_4h', 'neutral')
    )
    
    return prompt
