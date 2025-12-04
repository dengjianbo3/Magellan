"""
Trade Executor Agent - 智能交易执行决策Agent

职责:
1. 理解Leader的会议总结
2. 分析所有专家的投票
3. 考虑当前持仓状态
4. 做出独立的交易决策
5. 输出结构化的交易指令

设计理念:
- 不依赖固定格式或标记
- 完全基于语义理解
- 支持多种LLM和输出格式
- 鲁棒且可测试
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.models.trading_models import TradingSignal
from app.core.trading.position_context import PositionContext

logger = logging.getLogger(__name__)


class TradeExecutorAgent:
    """
    交易执行决策Agent
    
    这是一个真正的智能体，而不是简单的执行器。
    它能够:
    - 理解会议讨论的语义
    - 综合多个专家的意见
    - 考虑当前账户和持仓状态
    - 做出独立的交易决策
    """
    
    def __init__(self, agent_instance, toolkit, config):
        """
        初始化TradeExecutor
        
        Args:
            agent_instance: LLM Agent实例
            toolkit: 交易工具集（用于获取价格等）
            config: 交易配置
        """
        self.agent = agent_instance
        self.toolkit = toolkit
        self.config = config
        self.logger = logger
        
        # 🔧 验证必需的依赖
        if not self.toolkit:
            raise RuntimeError("TradeExecutor requires toolkit")
        # 🔧 FIX: toolkit可能有_get_market_price而不是price_service
        # 检查toolkit是否有获取价格的能力
        if not (hasattr(self.toolkit, 'price_service') or hasattr(self.toolkit, '_get_market_price')):
            raise RuntimeError("Toolkit must have price_service or _get_market_price method")
        if not self.config:
            raise RuntimeError("TradeExecutor requires config")
    
    async def _get_current_price_safe(self) -> float:
        """
        安全地获取当前价格
        
        优先级:
        1. 从LLM的JSON响应中提取（如果已经提供）
        2. TradeExecutor Agent自己调用工具获取
        3. 直接调用toolkit方法（fallback）
        """
        try:
            # 方法1: 检查agent是否有工具调用能力
            # 如果agent可以调用工具，让它自己去获取价格
            if hasattr(self.agent, 'tools') and self.agent.tools:
                self.logger.info("[TradeExecutor] Agent有工具能力，让Agent自己获取价格")
                # Agent会在决策过程中自己调用工具
                # 这里返回一个占位符，实际价格会在决策中获取
                # 但为了兼容性，我们还是提供fallback
                pass
            
            # 方法2: 使用toolkit的_get_market_price方法（TradingToolkit）
            if hasattr(self.toolkit, '_get_market_price'):
                result = await self.toolkit._get_market_price()
                # _get_market_price返回格式化的字符串，需要解析
                if isinstance(result, str):
                    # 从返回的字符串中提取价格
                    import re
                    price_match = re.search(r'当前价格.*?(\d+(?:,\d+)*(?:\.\d+)?)', result)
                    if price_match:
                        price_str = price_match.group(1).replace(',', '')
                        price = float(price_str)
                        if price > 0:
                            self.logger.info(f"[TradeExecutor] 通过_get_market_price获取价格: ${price:,.2f}")
                            return price
                elif isinstance(result, (int, float)):
                    price = float(result)
                    if price > 0:
                        self.logger.info(f"[TradeExecutor] 通过_get_market_price获取价格: ${price:,.2f}")
                        return price
            
            # 方法3: 使用price_service（如果存在）
            if hasattr(self.toolkit, 'price_service') and self.toolkit.price_service:
                price = await self.toolkit.price_service.get_current_price()
                if price and price > 0:
                    self.logger.info(f"[TradeExecutor] 通过price_service获取价格: ${price:,.2f}")
                    return price
            
            # 方法4: 直接从paper_trader获取
            if hasattr(self.toolkit, 'paper_trader') and self.toolkit.paper_trader:
                if hasattr(self.toolkit.paper_trader, 'current_price'):
                    price = self.toolkit.paper_trader.current_price
                    if price and price > 0:
                        self.logger.info(f"[TradeExecutor] 通过paper_trader获取价格: ${price:,.2f}")
                        return price
                        
        except Exception as e:
            self.logger.error(f"[TradeExecutor] 获取价格失败: {e}", exc_info=True)
        
        # Fallback: 抛出异常，让上层处理
        raise RuntimeError("无法获取当前价格，所有价格获取方法都失败")
    
    def _get_config_value(self, key: str, default: Any) -> Any:
        """
        安全地获取config值
        
        Args:
            key: 配置键
            default: 默认值
        
        Returns:
            配置值或默认值
        """
        return getattr(self.config, key, default)
    
    async def analyze_and_decide(
        self,
        meeting_summary: str,
        agents_votes: Dict[str, str],
        position_context: PositionContext,
        message_history: Optional[List[Dict]] = None
    ) -> TradingSignal:
        """
        分析会议结果并做出交易决策
        
        这是TradeExecutor的核心方法，完全不依赖固定格式。
        
        Args:
            meeting_summary: Leader的会议总结文本
            agents_votes: 专家投票字典 {"TechnicalAnalyst": "long", ...}
            position_context: 当前持仓和账户状态
            message_history: 完整会议记录（可选）
        
        Returns:
            TradingSignal: 最终交易决策
        """
        try:
            self.logger.info("[TradeExecutor] 🤖 开始分析会议结果...")
            
            # 1. 构建决策prompt
            prompt = self._build_decision_prompt(
                meeting_summary=meeting_summary,
                agents_votes=agents_votes,
                position_context=position_context
            )
            
            self.logger.info("[TradeExecutor] 📝 Prompt已构建，调用LLM进行决策...")
            
            # 2. 调用LLM进行决策
            try:
                response = await self.agent.run(prompt)
                self.logger.info(f"[TradeExecutor] ✅ LLM响应成功: {response[:200]}...")
            except Exception as e:
                self.logger.error(f"[TradeExecutor] ❌ LLM调用失败: {e}")
                # LLM失败时，根据投票做简单决策
                return await self._fallback_decision(agents_votes, position_context)
            
            # 3. 解析决策（支持多种格式）
            signal = await self._parse_decision(response, position_context)
            
            # 4. 验证决策合理性
            validated_signal = await self._validate_decision(signal, position_context)
            
            self.logger.info(
                f"[TradeExecutor] ✅ 决策完成: {validated_signal.direction.upper()} "
                f"| 杠杆 {validated_signal.leverage}x "
                f"| 仓位 {validated_signal.amount_percent*100:.0f}% "
                f"| 信心度 {validated_signal.confidence}%"
            )
            
            return validated_signal
            
        except Exception as e:
            self.logger.error(f"[TradeExecutor] ❌ 决策过程失败: {e}", exc_info=True)
            # 出错时返回hold
            return await self._create_safe_hold_signal(
                position_context,
                f"TradeExecutor决策失败: {str(e)}"
            )
    
    def _build_decision_prompt(
        self,
        meeting_summary: str,
        agents_votes: Dict[str, str],
        position_context: PositionContext
    ) -> str:
        """
        构建TradeExecutor的决策prompt
        
        这个prompt设计为：
        - 清晰表达TradeExecutor的职责
        - 提供所有必要的上下文信息
        - 不强制输出格式
        - 鼓励独立思考
        """
        
        # 格式化持仓状态
        position_status = self._format_position_status(position_context)
        
        # 格式化投票统计
        vote_summary = self._format_vote_summary(agents_votes)
        
        # 计算共识度
        consensus_level = self._calculate_consensus_level(agents_votes)
        
        # 🔧 安全地获取config值
        max_leverage = self._get_config_value('max_leverage', 20)
        
        prompt = f"""# 交易执行决策任务

你是 **交易执行专员 (TradeExecutor)**，负责根据专家圆桌会议的讨论结果做出最终交易决策。

## 1. 当前账户和持仓状态

{position_status}

## 2. 专家投票统计

{vote_summary}

**共识度**: {consensus_level}

## 3. Leader的会议总结

{meeting_summary}

---

## 你的任务

基于以上所有信息，做出最终交易决策。

### 决策考虑因素

1. **专家共识**:
   - 高度共识 (3-4票一致): 可以更果断，使用中高杠杆 (5-10x)
   - 温和共识 (2-3票): 谨慎操作，低杠杆 (3-5x)
   - 意见分歧 (投票分散): 观望或极低仓位试探 (1-2x)

2. **当前持仓状态**:
   - **无持仓**: 评估是否开新仓
   - **有多仓且专家看多**: 考虑加仓或持有
   - **有多仓但专家看空**: 考虑平仓或反向
   - **有空仓且专家看空**: 考虑加仓或持有
   - **有空仓但专家看多**: 考虑平仓或反向

3. **风险管理**:
   - 在不确定时优先选择观望
   - 杠杆应与信心度严格对应
   - 止损止盈要合理（一般TP=8%, SL=3%）
   - 仓位不能超过可用资金

4. **Leader的建议**:
   - Leader的总结是重要参考，但你有完全自主权
   - 如果你认为Leader过于保守/激进，可以调整

---

## 输出格式

请按以下JSON格式输出你的决策（必须是有效的JSON）:

```json
{{
  "decision": "open_long",
  "reasoning": "3位专家看多，技术面趋势强劲，RSI虽超买但有上升空间。考虑到无持仓状态，建议开多仓试探，使用中等杠杆以平衡收益和风险。",
  "confidence": 75,
  "leverage": 5,
  "amount_percent": 0.5,
  "take_profit_price": 98000,
  "stop_loss_price": 92000
}}
```

**decision字段可选值**:
- `open_long`: 开多仓
- `open_short`: 开空仓
- `close_position`: 平仓
- `add_to_position`: 加仓（当前持仓方向）
- `hold`: 观望

**重要提示**:
1. reasoning必须引用具体的专家意见和数据
2. confidence范围0-100，必须真实反映你的信心
3. leverage范围1-{max_leverage}，必须与confidence对应
4. amount_percent范围0.0-1.0（即0%-100%）
5. 价格必须合理（TP>当前价>SL for long; SL>当前价>TP for short）

现在，请做出你的最终决策。输出JSON即可，不需要其他解释。
"""
        
        return prompt
    
    def _format_position_status(self, position_context: PositionContext) -> str:
        """格式化持仓状态为易读的文本"""
        
        if not position_context.has_position:
            return f"""- **持仓状态**: 无持仓
- **可用余额**: ${position_context.available_balance:,.2f}
- **总权益**: ${position_context.total_equity:,.2f}
- **可用保证金**: ${position_context.available_margin:,.2f}
"""
        
        # 🔧 安全地获取direction，防止None
        direction = position_context.direction or "unknown"
        
        pnl_sign = "+" if position_context.unrealized_pnl >= 0 else ""
        pnl_color = "📈" if position_context.unrealized_pnl >= 0 else "📉"
        
        return f"""- **持仓状态**: {direction.upper()} 仓
- **持仓方向**: {direction}
- **开仓价格**: ${position_context.entry_price:,.2f}
- **当前价格**: ${position_context.current_price:,.2f}
- **持仓数量**: {position_context.position_amount:.4f}
- **杠杆倍数**: {position_context.leverage}x
- **未实现盈亏**: {pnl_color} {pnl_sign}${position_context.unrealized_pnl:,.2f} ({pnl_sign}{position_context.unrealized_pnl_percent:.2f}%)
- **止盈价格**: ${position_context.take_profit_price:,.2f}
- **止损价格**: ${position_context.stop_loss_price:,.2f}
- **可用余额**: ${position_context.available_balance:,.2f}
- **总权益**: ${position_context.total_equity:,.2f}
"""
    
    def _format_vote_summary(self, agents_votes: Dict[str, str]) -> str:
        """格式化投票统计"""
        
        # 统计投票
        long_count = sum(1 for v in agents_votes.values() if v == 'long')
        short_count = sum(1 for v in agents_votes.values() if v == 'short')
        hold_count = sum(1 for v in agents_votes.values() if v == 'hold')
        
        # 构建详细列表
        vote_details = []
        for agent, vote in agents_votes.items():
            emoji = "🟢" if vote == "long" else "🔴" if vote == "short" else "⚪"
            vote_text = "做多" if vote == "long" else "做空" if vote == "short" else "观望"
            vote_details.append(f"  {emoji} **{agent}**: {vote_text}")
        
        vote_list = "\n".join(vote_details)
        
        return f"""**投票分布**: {long_count}票做多 / {short_count}票做空 / {hold_count}票观望

{vote_list}
"""
    
    def _calculate_consensus_level(self, agents_votes: Dict[str, str]) -> str:
        """计算共识度"""
        
        if not agents_votes:
            return "无投票"
        
        vote_counts = {}
        for vote in agents_votes.values():
            vote_counts[vote] = vote_counts.get(vote, 0) + 1
        
        max_count = max(vote_counts.values())
        total_count = len(agents_votes)
        
        if max_count >= 4:
            return "🟢 高度共识 (>= 4票)"
        elif max_count == 3:
            return "🟡 温和共识 (3票)"
        elif max_count == 2:
            return "🟠 弱共识 (2票)"
        else:
            return "🔴 完全分歧"
    
    async def _parse_decision(
        self,
        response: str,
        position_context: PositionContext
    ) -> TradingSignal:
        """
        解析TradeExecutor的决策
        
        支持多种格式（优先级从高到低）:
        1. JSON格式（最优先）
        2. 自然语言提取（备用）
        """
        
        self.logger.info("[TradeExecutor] 🔍 开始解析决策响应...")
        
        # 方法1: 提取JSON（优先）
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if not json_match:
            # 尝试找裸JSON
            json_match = re.search(r'\{[^}]*"decision"[^}]*\}', response, re.DOTALL)
        
        if json_match:
            try:
                json_str = json_match.group(1) if json_match.lastindex else json_match.group(0)
                data = json.loads(json_str)
                self.logger.info("[TradeExecutor] ✅ 成功解析JSON格式")
                return await self._build_signal_from_dict(data, position_context)
            except json.JSONDecodeError as e:
                self.logger.warning(f"[TradeExecutor] ⚠️ JSON解析失败: {e}")
        
        # 方法2: 自然语言提取（备用）
        self.logger.info("[TradeExecutor] 🔍 使用自然语言提取...")
        return await self._extract_from_natural_language(response, position_context)
    
    async def _build_signal_from_dict(
        self,
        data: Dict[str, Any],
        position_context: PositionContext
    ) -> TradingSignal:
        """从字典构建TradingSignal"""
        
        decision = data.get("decision", "hold")
        
        # 映射decision到direction
        direction_map = {
            "open_long": "long",
            "open_short": "short",
            "close_position": "close",
            "add_to_position": position_context.direction if position_context.has_position else "hold",
            "hold": "hold"
        }
        
        direction = direction_map.get(decision, "hold")
        
        # 🔧 安全地获取当前价格
        current_price = await self._get_current_price_safe()
        
        # 提取其他字段
        leverage = int(data.get("leverage", 1))
        amount_percent = float(data.get("amount_percent", 0.0))
        confidence = int(data.get("confidence", 50))
        reasoning = data.get("reasoning", "TradeExecutor的决策")
        
        # 获取止盈止损
        take_profit = float(data.get("take_profit_price", 0))
        stop_loss = float(data.get("stop_loss_price", 0))
        
        # 🔧 安全地获取config值
        tp_percent = self._get_config_value('default_take_profit_percent', 0.08)
        sl_percent = self._get_config_value('default_stop_loss_percent', 0.03)
        symbol = self._get_config_value('symbol', 'BTC-USDT-SWAP')
        
        # 如果没有提供TP/SL，使用默认值
        if take_profit == 0:
            if direction == "long":
                take_profit = current_price * (1 + tp_percent)
            elif direction == "short":
                take_profit = current_price * (1 - tp_percent)
            else:
                take_profit = current_price
        
        if stop_loss == 0:
            if direction == "long":
                stop_loss = current_price * (1 - sl_percent)
            elif direction == "short":
                stop_loss = current_price * (1 + sl_percent)
            else:
                stop_loss = current_price
        
        return TradingSignal(
            direction=direction,
            symbol=symbol,
            leverage=leverage,
            amount_percent=amount_percent,
            entry_price=current_price,
            take_profit_price=take_profit,
            stop_loss_price=stop_loss,
            confidence=confidence,
            reasoning=reasoning,
            agents_consensus={},
            timestamp=datetime.now()
        )
    
    async def _extract_from_natural_language(
        self,
        response: str,
        position_context: PositionContext
    ) -> TradingSignal:
        """
        从自然语言中提取决策（最后手段）
        
        示例:
        "我决定做多BTC，使用5倍杠杆，仓位50%，止盈98000，止损92000"
        """
        
        self.logger.info("[TradeExecutor] 📝 从自然语言中提取决策...")
        
        # 提取方向
        direction = "hold"
        if re.search(r'(做多|开多|买入|long|开仓.*多)', response, re.I):
            direction = "long"
        elif re.search(r'(做空|开空|卖出|short|开仓.*空)', response, re.I):
            direction = "short"
        elif re.search(r'(平仓|关闭|close)', response, re.I):
            direction = "close"
        elif re.search(r'(观望|等待|hold|不操作)', response, re.I):
            direction = "hold"
        
        self.logger.info(f"[TradeExecutor] 提取方向: {direction}")
        
        # 🔧 安全地获取config值
        max_leverage = self._get_config_value('max_leverage', 20)
        tp_percent = self._get_config_value('default_take_profit_percent', 0.08)
        sl_percent = self._get_config_value('default_stop_loss_percent', 0.03)
        symbol = self._get_config_value('symbol', 'BTC-USDT-SWAP')
        
        # 提取杠杆
        leverage_match = re.search(r'(\d+)\s*[倍xX×]', response)
        leverage = int(leverage_match.group(1)) if leverage_match else 1
        leverage = min(max(leverage, 1), max_leverage)
        
        # 提取仓位
        position_match = re.search(r'仓位[：:]\s*(\d+)%', response)
        if not position_match:
            position_match = re.search(r'(\d+)%.*仓', response)
        amount_percent = float(position_match.group(1)) / 100 if position_match else 0.4
        amount_percent = min(max(amount_percent, 0.0), 1.0)
        
        # 提取价格
        tp_match = re.search(r'止[盈贏][：:]?\s*(\d+)', response)
        sl_match = re.search(r'止[损損][：:]?\s*(\d+)', response)
        
        # 提取信心度
        confidence_match = re.search(r'信心[度]?[：:]?\s*(\d+)', response)
        confidence = int(confidence_match.group(1)) if confidence_match else 50
        confidence = min(max(confidence, 0), 100)
        
        # 🔧 安全地获取当前价格
        current_price = await self._get_current_price_safe()
        
        # 计算止盈止损
        if tp_match:
            take_profit = float(tp_match.group(1))
        else:
            if direction == "long":
                take_profit = current_price * (1 + tp_percent)
            elif direction == "short":
                take_profit = current_price * (1 - tp_percent)
            else:
                take_profit = current_price
        
        if sl_match:
            stop_loss = float(sl_match.group(1))
        else:
            if direction == "long":
                stop_loss = current_price * (1 - sl_percent)
            elif direction == "short":
                stop_loss = current_price * (1 + sl_percent)
            else:
                stop_loss = current_price
        
        self.logger.info(
            f"[TradeExecutor] 提取结果: {direction} | "
            f"杠杆 {leverage}x | 仓位 {amount_percent*100:.0f}% | "
            f"信心度 {confidence}%"
        )
        
        return TradingSignal(
            direction=direction,
            symbol=symbol,
            leverage=leverage,
            amount_percent=amount_percent,
            entry_price=current_price,
            take_profit_price=take_profit,
            stop_loss_price=stop_loss,
            confidence=confidence,
            reasoning=response[:500],  # 取前500字符作为理由
            agents_consensus={},
            timestamp=datetime.now()
        )
    
    async def _validate_decision(
        self,
        signal: TradingSignal,
        position_context: PositionContext
    ) -> TradingSignal:
        """
        验证决策的合理性并进行必要的调整
        
        验证项:
        1. 杠杆在允许范围内
        2. 仓位不超过可用资金
        3. 止盈止损价格合理
        4. 信心度与杠杆对应
        """
        
        self.logger.info("[TradeExecutor] 🔍 验证决策合理性...")
        
        # 🔧 安全地获取config值
        max_leverage = self._get_config_value('max_leverage', 20)
        tp_percent = self._get_config_value('default_take_profit_percent', 0.08)
        sl_percent = self._get_config_value('default_stop_loss_percent', 0.03)
        
        # 1. 限制杠杆
        if signal.leverage > max_leverage:
            self.logger.warning(
                f"[TradeExecutor] ⚠️ 杠杆 {signal.leverage}x 超过上限 {max_leverage}x，已调整"
            )
            signal.leverage = max_leverage
        
        if signal.leverage < 1:
            signal.leverage = 1
        
        # 2. 限制仓位
        if signal.amount_percent > 1.0:
            self.logger.warning(
                f"[TradeExecutor] ⚠️ 仓位 {signal.amount_percent*100:.0f}% 超过100%，已调整"
            )
            signal.amount_percent = 1.0
        
        if signal.amount_percent < 0:
            signal.amount_percent = 0
        
        # 3. 验证止盈止损
        current_price = signal.entry_price
        
        if signal.direction == "long":
            if signal.take_profit_price <= current_price:
                self.logger.warning("[TradeExecutor] ⚠️ 多仓止盈价格不合理，使用默认值")
                signal.take_profit_price = current_price * (1 + tp_percent)
            
            if signal.stop_loss_price >= current_price:
                self.logger.warning("[TradeExecutor] ⚠️ 多仓止损价格不合理，使用默认值")
                signal.stop_loss_price = current_price * (1 - sl_percent)
        
        elif signal.direction == "short":
            if signal.take_profit_price >= current_price:
                self.logger.warning("[TradeExecutor] ⚠️ 空仓止盈价格不合理，使用默认值")
                signal.take_profit_price = current_price * (1 - tp_percent)
            
            if signal.stop_loss_price <= current_price:
                self.logger.warning("[TradeExecutor] ⚠️ 空仓止损价格不合理，使用默认值")
                signal.stop_loss_price = current_price * (1 + sl_percent)
        
        # 4. 限制信心度
        if signal.confidence > 100:
            signal.confidence = 100
        if signal.confidence < 0:
            signal.confidence = 0
        
        self.logger.info("[TradeExecutor] ✅ 决策验证完成")
        
        return signal
    
    async def _fallback_decision(
        self,
        agents_votes: Dict[str, str],
        position_context: PositionContext
    ) -> TradingSignal:
        """
        当LLM调用失败时的备用决策逻辑
        
        基于专家投票做简单的多数决策
        """
        
        self.logger.info("[TradeExecutor] 🔄 使用备用决策逻辑（基于投票）...")
        
        # 统计投票
        long_count = sum(1 for v in agents_votes.values() if v == 'long')
        short_count = sum(1 for v in agents_votes.values() if v == 'short')
        hold_count = sum(1 for v in agents_votes.values() if v == 'hold')
        
        total_votes = len(agents_votes)
        
        # 多数决策
        if long_count >= total_votes * 0.6:  # 60%以上看多
            direction = "long"
            confidence = int(long_count / total_votes * 100)
        elif short_count >= total_votes * 0.6:  # 60%以上看空
            direction = "short"
            confidence = int(short_count / total_votes * 100)
        else:
            direction = "hold"
            confidence = 0
        
        # 根据信心度设置杠杆
        if confidence >= 80:
            leverage = 8
        elif confidence >= 60:
            leverage = 5
        else:
            leverage = 3
        
        # 🔧 安全地获取当前价格和config值
        current_price = await self._get_current_price_safe()
        symbol = self._get_config_value('symbol', 'BTC-USDT-SWAP')
        
        return TradingSignal(
            direction=direction,
            symbol=symbol,
            leverage=leverage,
            amount_percent=0.4,  # 保守仓位
            entry_price=current_price,
            take_profit_price=current_price * (1.05 if direction == "long" else 0.95),
            stop_loss_price=current_price * (0.97 if direction == "long" else 1.03),
            confidence=confidence,
            reasoning=f"LLM调用失败，基于投票备用决策: {long_count}票多/{short_count}票空/{hold_count}票观望",
            agents_consensus=agents_votes,
            timestamp=datetime.now()
        )
    
    async def _create_safe_hold_signal(
        self,
        position_context: PositionContext,
        reason: str
    ) -> TradingSignal:
        """创建一个安全的hold信号"""
        
        # 🔧 安全地获取当前价格和config值
        current_price = await self._get_current_price_safe()
        symbol = self._get_config_value('symbol', 'BTC-USDT-SWAP')
        
        return TradingSignal(
            direction="hold",
            symbol=symbol,
            leverage=1,
            amount_percent=0.0,
            entry_price=current_price,
            take_profit_price=current_price,
            stop_loss_price=current_price,
            confidence=0,
            reasoning=reason,
            agents_consensus={},
            timestamp=datetime.now()
        )
