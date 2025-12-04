"""
Trade Executor - 交易执行专员

职责：
1. 接收Leader的决策指令（TradingSignal）
2. 进行二次验证（账户状态、持仓检查）
3. 执行实际的交易工具调用
4. 返回执行结果

Architecture:
- Leader: 决策者 (生成 TradingSignal)
- TradeExecutor: 执行者 (执行 TradingSignal)
- 符合单一职责原则和关注点分离原则
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
    交易执行专员
    
    负责执行Leader的交易决策，包括：
    - 二次验证决策的合理性
    - 检查账户状态和风险限制
    - 调用实际的交易工具
    - 记录详细的执行日志
    """
    
    def __init__(self, toolkit, paper_trader=None):
        """
        Initialize TradeExecutor
        
        Args:
            toolkit: TradingToolkit instance with execution tools
            paper_trader: PaperTrader instance for direct execution (optional)
        """
        self.toolkit = toolkit
        self.paper_trader = paper_trader
        self.name = "交易执行专员"
        self.id = "TradeExecutor"
        
        logger.info(f"[{self.name}] Initialized with toolkit: {type(toolkit).__name__}")
    
    async def execute_signal(
        self, 
        signal: 'TradingSignal',
        position_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        执行交易信号
        
        执行流程:
        1. 验证信号完整性
        2. 检查账户状态
        3. 检查持仓冲突
        4. 执行交易工具
        5. 返回执行结果
        
        Args:
            signal: Leader生成的交易信号
            position_info: 当前持仓信息（包括position, account, limits等）
            
        Returns:
            执行结果字典 {
                "status": "success" | "rejected" | "error",
                "action": "opened_long" | "opened_short" | "hold" | ...,
                "reason": "...",
                "details": {...}
            }
        """
        logger.info(f"[{self.name}] ========================================")
        logger.info(f"[{self.name}] 收到Leader的交易决策")
        logger.info(f"[{self.name}] 决策方向: {signal.direction}")
        logger.info(f"[{self.name}] 信心度: {signal.confidence}%")
        logger.info(f"[{self.name}] ========================================")
        
        # Step 1: 验证信号完整性
        validation_result = self._validate_signal(signal)
        if not validation_result['valid']:
            logger.error(f"[{self.name}] ❌ 信号验证失败: {validation_result['reason']}")
            return {
                "status": "rejected",
                "action": "validation_failed",
                "reason": validation_result['reason'],
                "details": {}
            }
        
        logger.info(f"[{self.name}] ✅ 信号验证通过")
        
        # Step 2: 检查账户状态
        account_check = await self._check_account_status()
        if not account_check['ok']:
            logger.error(f"[{self.name}] ❌ 账户检查失败: {account_check['reason']}")
            return {
                "status": "rejected",
                "action": "account_check_failed",
                "reason": account_check['reason'],
                "details": account_check
            }
        
        logger.info(f"[{self.name}] ✅ 账户状态正常")
        
        # Step 3: 检查持仓冲突（如果是开仓操作）
        if signal.direction in ["long", "short"]:
            conflict_check = self._check_position_conflict(signal, position_info)
            if conflict_check['has_conflict']:
                logger.warning(f"[{self.name}] ⚠️ 持仓冲突: {conflict_check['reason']}")
                return {
                    "status": "rejected",
                    "action": "position_conflict",
                    "reason": conflict_check['reason'],
                    "details": conflict_check
                }
            
            logger.info(f"[{self.name}] ✅ 无持仓冲突")
        
        # Step 4: 执行交易工具
        logger.info(f"[{self.name}] 🚀 开始执行交易...")
        
        try:
            execution_result = await self._execute_trade(signal)
            
            if execution_result.get('status') == 'success':
                logger.info(f"[{self.name}] ✅ 交易执行成功!")
                logger.info(f"[{self.name}] 操作: {execution_result.get('action')}")
                logger.info(f"[{self.name}] 详情: {execution_result.get('details', {})}")
            else:
                logger.error(f"[{self.name}] ❌ 交易执行失败: {execution_result.get('reason')}")
            
            return execution_result
            
        except Exception as e:
            logger.error(f"[{self.name}] ❌ 交易执行异常: {e}", exc_info=True)
            return {
                "status": "error",
                "action": "execution_error",
                "reason": f"执行异常: {str(e)}",
                "details": {}
            }
    
    def _validate_signal(self, signal: 'TradingSignal') -> Dict[str, Any]:
        """
        验证信号完整性
        
        检查:
        - direction不为空
        - confidence在合理范围内
        - 如果是开仓，leverage/amount_percent必须合理
        - 止盈止损价格必须设置
        """
        if not signal.direction:
            return {"valid": False, "reason": "决策方向为空"}
        
        if signal.direction not in ["long", "short", "hold", "close"]:
            return {"valid": False, "reason": f"未知的决策方向: {signal.direction}"}
        
        if not (0 <= signal.confidence <= 100):
            return {"valid": False, "reason": f"信心度超出范围: {signal.confidence}"}
        
        # 如果是开仓操作，检查参数
        if signal.direction in ["long", "short"]:
            if signal.leverage < 1 or signal.leverage > 20:
                return {"valid": False, "reason": f"杠杆倍数不合理: {signal.leverage}"}
            
            if signal.amount_percent <= 0 or signal.amount_percent > 100:
                return {"valid": False, "reason": f"仓位比例不合理: {signal.amount_percent}%"}
            
            # 检查止盈止损
            if signal.take_profit_price <= 0 or signal.stop_loss_price <= 0:
                return {"valid": False, "reason": "止盈止损价格未设置"}
        
        return {"valid": True, "reason": ""}
    
    async def _check_account_status(self) -> Dict[str, Any]:
        """
        检查账户状态
        
        检查:
        - 账户是否可用
        - 余额是否充足（至少10 USDT用于交易）
        """
        if not self.paper_trader:
            # 如果没有paper_trader，使用toolkit获取账户信息
            # 这里简化处理，默认通过
            logger.warning(f"[{self.name}] No paper_trader provided, skipping detailed account check")
            return {"ok": True, "reason": ""}
        
        try:
            # 获取账户信息
            account = self.paper_trader.get_account_status()
            balance = account.get('balance', 0)
            
            # 检查余额是否充足
            min_balance_required = 10  # 至少10 USDT
            if balance < min_balance_required:
                return {
                    "ok": False, 
                    "reason": f"余额不足: {balance:.2f} USDT < {min_balance_required} USDT",
                    "balance": balance
                }
            
            return {"ok": True, "reason": "", "balance": balance}
            
        except Exception as e:
            logger.error(f"[{self.name}] 检查账户状态失败: {e}")
            return {"ok": False, "reason": f"账户检查异常: {str(e)}"}
    
    def _check_position_conflict(
        self, 
        signal: 'TradingSignal',
        position_info: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        检查持仓冲突
        
        检查:
        - 是否已有持仓（如果有，不能直接开新仓）
        - 持仓方向是否与信号冲突
        
        Args:
            signal: 交易信号
            position_info: 持仓信息 {
                "has_position": bool,
                "current_position": {...},
                "can_add": bool,
                ...
            }
        """
        if not position_info:
            # 没有提供持仓信息，默认无冲突
            return {"has_conflict": False, "reason": ""}
        
        has_position = position_info.get('has_position', False)
        
        if not has_position:
            # 无持仓，可以自由开仓
            return {"has_conflict": False, "reason": ""}
        
        # 有持仓，检查是否冲突
        current_position = position_info.get('current_position', {})
        current_direction = current_position.get('direction', '')
        
        # 如果要开同方向的仓，检查是否允许追加
        if signal.direction == current_direction:
            can_add = position_info.get('can_add', False)
            if not can_add:
                return {
                    "has_conflict": True,
                    "reason": f"已有{current_direction}持仓，且已达仓位上限，不能追加"
                }
            # 可以追加
            return {"has_conflict": False, "reason": "可以追加持仓"}
        
        # 如果要开反方向的仓，这是冲突
        if signal.direction in ["long", "short"]:
            return {
                "has_conflict": True,
                "reason": f"已有{current_direction}持仓，不能直接开{signal.direction}仓。请先平仓或使用反向操作。"
            }
        
        return {"has_conflict": False, "reason": ""}
    
    async def _execute_trade(self, signal: 'TradingSignal') -> Dict[str, Any]:
        """
        执行实际的交易操作
        
        根据signal.direction调用对应的工具:
        - long: open_long
        - short: open_short
        - hold: 观望（不执行）
        - close: close_position
        """
        direction = signal.direction
        
        logger.info(f"[{self.name}] 执行 {direction} 操作")
        
        # Hold - 观望
        if direction == "hold":
            return {
                "status": "success",
                "action": "hold",
                "reason": signal.reasoning or "观望等待更好时机",
                "details": {
                    "confidence": signal.confidence,
                    "reasoning": signal.reasoning
                }
            }
        
        # Close - 平仓
        if direction == "close":
            if self.paper_trader:
                result = await self.paper_trader.close_position(
                    reason=signal.reasoning or "Leader决策平仓"
                )
            else:
                # 使用toolkit
                close_tool = self.toolkit._tools.get('close_position')
                if not close_tool:
                    return {
                        "status": "error",
                        "action": "close_position",
                        "reason": "close_position工具未找到",
                        "details": {}
                    }
                result = await close_tool.execute(reason=signal.reasoning or "Leader决策平仓")
            
            # 解析result
            if isinstance(result, dict):
                if result.get('status') == 'success':
                    return {
                        "status": "success",
                        "action": "closed_position",
                        "reason": "平仓成功",
                        "details": result
                    }
                else:
                    return {
                        "status": "error",
                        "action": "close_position",
                        "reason": result.get('message', '平仓失败'),
                        "details": result
                    }
            else:
                # result是字符串
                return {
                    "status": "success",
                    "action": "closed_position",
                    "reason": str(result),
                    "details": {}
                }
        
        # Long/Short - 开仓
        if direction in ["long", "short"]:
            # 准备参数
            params = {
                "symbol": signal.symbol,
                "leverage": signal.leverage,
                "amount_percent": signal.amount_percent,
                "take_profit_price": signal.take_profit_price,
                "stop_loss_price": signal.stop_loss_price,
                "reason": signal.reasoning or f"Leader决策做{direction}"
            }
            
            # 调用工具
            if self.paper_trader:
                # 直接调用paper_trader
                if direction == "long":
                    result = await self.paper_trader.open_long(**params)
                else:
                    result = await self.paper_trader.open_short(**params)
            else:
                # 使用toolkit
                tool_name = "open_long" if direction == "long" else "open_short"
                tool = self.toolkit._tools.get(tool_name)
                if not tool:
                    return {
                        "status": "error",
                        "action": tool_name,
                        "reason": f"{tool_name}工具未找到",
                        "details": {}
                    }
                result = await tool.execute(**params)
            
            # 解析result
            if isinstance(result, dict):
                if result.get('status') == 'success':
                    return {
                        "status": "success",
                        "action": f"opened_{direction}",
                        "reason": f"开{direction}仓成功",
                        "details": result
                    }
                else:
                    return {
                        "status": "error",
                        "action": f"open_{direction}",
                        "reason": result.get('message', f'开{direction}仓失败'),
                        "details": result
                    }
            else:
                # result是字符串
                return {
                    "status": "success",
                    "action": f"opened_{direction}",
                    "reason": str(result),
                    "details": {}
                }
        
        # 未知操作
        return {
            "status": "error",
            "action": "unknown",
            "reason": f"未知的操作类型: {direction}",
            "details": {}
        }
