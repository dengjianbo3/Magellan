"""
FastMonitor - 快速硬条件监控器

Layer 1: 无 LLM 调用，纯规则检测
用于快速检测市场异常情况，触发 Layer 2 (TriggerAgent) 深度分析

支持的硬条件：
1. 价格急涨急跌 (1m/5m/15m)
2. 成交量异常 (vs 均值)
3. 资金费率突变
4. 持仓量变化
5. RSI 极端值
6. EMA 价格偏离
"""

import asyncio
import aiohttp
import logging
import os
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


def _get_env_float(key: str, default: float) -> float:
    """Get float from environment variable"""
    val = os.getenv(key)
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return default


def _get_env_int(key: str, default: int) -> int:
    """Get int from environment variable"""
    val = os.getenv(key)
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return default


@dataclass
class FastTriggerCondition:
    """单个触发条件"""
    name: str           # 条件名称
    value: float        # 当前值
    threshold: float    # 阈值
    direction: str      # "above" / "below" / "both"
    urgency: str        # "low" / "medium" / "high" / "critical"
    description: str    # 可读描述


@dataclass
class FastTriggerResult:
    """快速触发结果"""
    should_trigger: bool = False
    conditions: List[FastTriggerCondition] = field(default_factory=list)
    urgency: str = "low"  # 最高紧急程度
    timestamp: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "should_trigger": self.should_trigger,
            "conditions": [
                {
                    "name": c.name,
                    "value": c.value,
                    "threshold": c.threshold,
                    "urgency": c.urgency,
                    "description": c.description
                }
                for c in self.conditions
            ],
            "urgency": self.urgency,
            "timestamp": self.timestamp
        }


class FastMonitorConfig:
    """
    快速监控配置阈值
    
    All thresholds are configurable via environment variables.
    """
    
    def __init__(self):
        # ===== 价格急变 =====
        self.PRICE_SPIKE_1M = _get_env_float("MONITOR_PRICE_SPIKE_1M", 1.5)       # 1分钟变动 ±1.5%
        self.PRICE_SPIKE_5M = _get_env_float("MONITOR_PRICE_SPIKE_5M", 2.5)       # 5分钟变动 ±2.5%
        self.PRICE_SPIKE_15M = _get_env_float("MONITOR_PRICE_SPIKE_15M", 4.0)     # 15分钟变动 ±4.0%
        
        # ===== 成交量异常 =====
        self.VOLUME_SPIKE_5M = _get_env_float("MONITOR_VOLUME_SPIKE_5M", 3.0)     # 5分钟成交量 > 3x 均值
        self.VOLUME_SPIKE_1M = _get_env_float("MONITOR_VOLUME_SPIKE_1M", 5.0)     # 1分钟成交量 > 5x 均值
        
        # ===== 资金费率 =====
        self.FUNDING_RATE_EXTREME = _get_env_float("MONITOR_FUNDING_EXTREME", 0.1)    # 资金费率 > 0.1% (每8h)
        self.FUNDING_RATE_CHANGE = _get_env_float("MONITOR_FUNDING_CHANGE", 0.05)     # 资金费率变化 > 0.05%
        
        # ===== 持仓量 =====
        self.OI_CHANGE_15M = _get_env_float("MONITOR_OI_CHANGE_15M", 3.0)         # 15分钟 OI 变化 > 3%
        self.OI_CHANGE_1H = _get_env_float("MONITOR_OI_CHANGE_1H", 5.0)           # 1小时 OI 变化 > 5%
        
        # ===== 技术指标 =====
        self.RSI_OVERBOUGHT = _get_env_int("MONITOR_RSI_OVERBOUGHT", 85)          # RSI > 85 极端超买
        self.RSI_OVERSOLD = _get_env_int("MONITOR_RSI_OVERSOLD", 15)              # RSI < 15 极端超卖
        self.EMA_DEVIATION = _get_env_float("MONITOR_EMA_DEVIATION", 5.0)         # 价格 vs EMA20 偏离 > 5%


class FastMonitor:
    """
    快速硬条件监控器
    
    每 1-5 分钟运行一次，检测市场异常情况
    无 LLM 调用开销，纯规则计算
    """
    
    def __init__(
        self,
        symbol: str = "BTC-USDT-SWAP",
        config: FastMonitorConfig = None
    ):
        self.symbol = symbol
        self.config = config or FastMonitorConfig()
        self.base_url = "https://www.okx.com"
        
        # 价格历史 (用于计算变化)
        self._price_history: deque = deque(maxlen=60)  # 60个数据点
        self._last_price_time: Optional[datetime] = None
        
        # 缓存数据
        self._last_funding_rate: Optional[float] = None
        self._last_open_interest: Optional[float] = None
        self._last_oi_time: Optional[datetime] = None
        
        logger.info(f"[FastMonitor] Initialized for {symbol}")
    
    async def check(self) -> FastTriggerResult:
        """
        执行所有硬条件检测
        
        Returns:
            FastTriggerResult - 包含是否触发及触发条件详情
        """
        triggered_conditions: List[FastTriggerCondition] = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # 并行获取所有需要的数据
                tasks = [
                    self._fetch_ticker(session),
                    self._fetch_candles(session, "1m", 10),
                    self._fetch_candles(session, "5m", 25),
                    self._fetch_candles(session, "15m", 50),
                    self._fetch_funding_rate(session),
                    self._fetch_open_interest(session),
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                ticker = results[0] if not isinstance(results[0], Exception) else {}
                candles_1m = results[1] if not isinstance(results[1], Exception) else []
                candles_5m = results[2] if not isinstance(results[2], Exception) else []
                candles_15m = results[3] if not isinstance(results[3], Exception) else []
                funding_data = results[4] if not isinstance(results[4], Exception) else {}
                oi_data = results[5] if not isinstance(results[5], Exception) else {}
                
                current_price = float(ticker.get("last", 0)) if ticker else 0
                
                # 1. 价格急变检测
                price_conditions = self._check_price_spikes(
                    candles_1m, candles_5m, candles_15m
                )
                triggered_conditions.extend(price_conditions)
                
                # 2. 成交量异常检测
                volume_conditions = self._check_volume_spikes(candles_1m, candles_5m)
                triggered_conditions.extend(volume_conditions)
                
                # 3. 资金费率检测
                funding_conditions = self._check_funding_rate(funding_data)
                triggered_conditions.extend(funding_conditions)
                
                # 4. 持仓量变化检测
                oi_conditions = self._check_open_interest(oi_data)
                triggered_conditions.extend(oi_conditions)
                
                # 5. RSI 极端值检测
                rsi_conditions = self._check_rsi_extreme(candles_15m)
                triggered_conditions.extend(rsi_conditions)
                
                # 6. EMA 偏离检测
                ema_conditions = self._check_ema_deviation(candles_15m, current_price)
                triggered_conditions.extend(ema_conditions)
                
        except Exception as e:
            logger.error(f"[FastMonitor] Check failed: {e}")
            import traceback
            traceback.print_exc()
        
        # 确定最高紧急程度
        urgency_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        max_urgency = "low"
        for cond in triggered_conditions:
            if urgency_order.get(cond.urgency, 0) > urgency_order.get(max_urgency, 0):
                max_urgency = cond.urgency
        
        result = FastTriggerResult(
            should_trigger=len(triggered_conditions) > 0,
            conditions=triggered_conditions,
            urgency=max_urgency,
            timestamp=datetime.now().isoformat()
        )
        
        if result.should_trigger:
            conditions_str = ", ".join([c.name for c in triggered_conditions])
            logger.warning(f"[FastMonitor] 🚨 Triggered: {conditions_str} (Urgency: {max_urgency})")
        else:
            logger.debug("[FastMonitor] ✅ No triggers")
        
        return result
    
    # ========== 价格检测 ==========
    
    def _check_price_spikes(
        self,
        candles_1m: List[Dict],
        candles_5m: List[Dict],
        candles_15m: List[Dict]
    ) -> List[FastTriggerCondition]:
        """检测价格急涨急跌"""
        conditions = []
        
        # 1分钟变动
        if len(candles_1m) >= 2:
            change_1m = self._calc_price_change(candles_1m, 1)
            if abs(change_1m) >= self.config.PRICE_SPIKE_1M:
                conditions.append(FastTriggerCondition(
                    name="price_spike_1m",
                    value=change_1m,
                    threshold=self.config.PRICE_SPIKE_1M,
                    direction="up" if change_1m > 0 else "down",
                    urgency="high" if abs(change_1m) >= 2.5 else "medium",
                    description=f"1分钟价格{'暴涨' if change_1m > 0 else '暴跌'} {abs(change_1m):.2f}%"
                ))
        
        # 5分钟变动
        if len(candles_5m) >= 2:
            change_5m = self._calc_price_change(candles_5m, 1)
            if abs(change_5m) >= self.config.PRICE_SPIKE_5M:
                conditions.append(FastTriggerCondition(
                    name="price_spike_5m",
                    value=change_5m,
                    threshold=self.config.PRICE_SPIKE_5M,
                    direction="up" if change_5m > 0 else "down",
                    urgency="high" if abs(change_5m) >= 4.0 else "medium",
                    description=f"5分钟价格{'急涨' if change_5m > 0 else '急跌'} {abs(change_5m):.2f}%"
                ))
        
        # 15分钟变动
        if len(candles_15m) >= 2:
            change_15m = self._calc_price_change(candles_15m, 1)
            if abs(change_15m) >= self.config.PRICE_SPIKE_15M:
                conditions.append(FastTriggerCondition(
                    name="price_spike_15m",
                    value=change_15m,
                    threshold=self.config.PRICE_SPIKE_15M,
                    direction="up" if change_15m > 0 else "down",
                    urgency="critical" if abs(change_15m) >= 6.0 else "high",
                    description=f"15分钟价格{'大涨' if change_15m > 0 else '大跌'} {abs(change_15m):.2f}%"
                ))
        
        return conditions
    
    # ========== 成交量检测 ==========
    
    def _check_volume_spikes(
        self,
        candles_1m: List[Dict],
        candles_5m: List[Dict]
    ) -> List[FastTriggerCondition]:
        """检测成交量异常"""
        conditions = []
        
        # 1分钟成交量 vs 均值
        if len(candles_1m) >= 6:
            current_vol = candles_1m[0].get("volume", 0)
            avg_vol = sum([c.get("volume", 0) for c in candles_1m[1:6]]) / 5
            if avg_vol > 0:
                ratio = current_vol / avg_vol
                if ratio >= self.config.VOLUME_SPIKE_1M:
                    conditions.append(FastTriggerCondition(
                        name="volume_spike_1m",
                        value=ratio,
                        threshold=self.config.VOLUME_SPIKE_1M,
                        direction="both",
                        urgency="high",
                        description=f"1分钟成交量异常放大 {ratio:.1f}x"
                    ))
        
        # 5分钟成交量 vs 均值
        if len(candles_5m) >= 21:
            current_vol = candles_5m[0].get("volume", 0)
            avg_vol = sum([c.get("volume", 0) for c in candles_5m[1:21]]) / 20
            if avg_vol > 0:
                ratio = current_vol / avg_vol
                if ratio >= self.config.VOLUME_SPIKE_5M:
                    conditions.append(FastTriggerCondition(
                        name="volume_spike_5m",
                        value=ratio,
                        threshold=self.config.VOLUME_SPIKE_5M,
                        direction="both",
                        urgency="medium",
                        description=f"5分钟成交量放大 {ratio:.1f}x"
                    ))
        
        return conditions
    
    # ========== 资金费率检测 ==========
    
    def _check_funding_rate(self, funding_data: Dict) -> List[FastTriggerCondition]:
        """检测资金费率异常"""
        conditions = []
        
        if not funding_data:
            return conditions
        
        # Safe float conversion helper
        def safe_float(val, default=0.0):
            try:
                if val is None or val == "":
                    return default
                return float(val)
            except (ValueError, TypeError):
                return default
        
        current_rate = safe_float(funding_data.get("fundingRate")) * 100  # 转为百分比
        next_rate = safe_float(funding_data.get("nextFundingRate")) * 100
        
        # 当前资金费率极端
        if abs(current_rate) >= self.config.FUNDING_RATE_EXTREME:
            conditions.append(FastTriggerCondition(
                name="funding_rate_extreme",
                value=current_rate,
                threshold=self.config.FUNDING_RATE_EXTREME,
                direction="both",
                urgency="high",
                description=f"资金费率极端: {current_rate:.4f}% ({'多头拥挤' if current_rate > 0 else '空头拥挤'})"
            ))
        
        # 资金费率变化 (如果有历史数据)
        if self._last_funding_rate is not None:
            rate_change = abs(current_rate - self._last_funding_rate)
            if rate_change >= self.config.FUNDING_RATE_CHANGE:
                conditions.append(FastTriggerCondition(
                    name="funding_rate_change",
                    value=rate_change,
                    threshold=self.config.FUNDING_RATE_CHANGE,
                    direction="both",
                    urgency="medium",
                    description=f"资金费率突变 {rate_change:.4f}%"
                ))
        
        # 更新历史
        self._last_funding_rate = current_rate
        
        return conditions
    
    # ========== 持仓量检测 ==========
    
    def _check_open_interest(self, oi_data: Dict) -> List[FastTriggerCondition]:
        """检测持仓量变化"""
        conditions = []
        
        if not oi_data:
            return conditions
        
        current_oi = float(oi_data.get("oi", 0))
        
        if self._last_open_interest is not None and self._last_open_interest > 0:
            oi_change = (current_oi - self._last_open_interest) / self._last_open_interest * 100
            
            # 15分钟级别判断 (假设 check 频率约 5 分钟)
            if abs(oi_change) >= self.config.OI_CHANGE_15M:
                conditions.append(FastTriggerCondition(
                    name="open_interest_change",
                    value=oi_change,
                    threshold=self.config.OI_CHANGE_15M,
                    direction="up" if oi_change > 0 else "down",
                    urgency="medium",
                    description=f"持仓量{'激增' if oi_change > 0 else '骤降'} {abs(oi_change):.2f}%"
                ))
        
        # 更新历史
        self._last_open_interest = current_oi
        self._last_oi_time = datetime.now()
        
        return conditions
    
    # ========== RSI 检测 ==========
    
    def _check_rsi_extreme(self, candles_15m: List[Dict]) -> List[FastTriggerCondition]:
        """检测 RSI 极端值"""
        conditions = []
        
        if len(candles_15m) < 15:
            return conditions
        
        rsi = self._calculate_rsi(candles_15m, 14)
        
        if rsi >= self.config.RSI_OVERBOUGHT:
            conditions.append(FastTriggerCondition(
                name="rsi_overbought",
                value=rsi,
                threshold=self.config.RSI_OVERBOUGHT,
                direction="above",
                urgency="medium",
                description=f"RSI(15m) 极端超买: {rsi:.1f}"
            ))
        elif rsi <= self.config.RSI_OVERSOLD:
            conditions.append(FastTriggerCondition(
                name="rsi_oversold",
                value=rsi,
                threshold=self.config.RSI_OVERSOLD,
                direction="below",
                urgency="medium",
                description=f"RSI(15m) 极端超卖: {rsi:.1f}"
            ))
        
        return conditions
    
    # ========== EMA 偏离检测 ==========
    
    def _check_ema_deviation(
        self,
        candles_15m: List[Dict],
        current_price: float
    ) -> List[FastTriggerCondition]:
        """检测价格与 EMA20 的偏离"""
        conditions = []
        
        if len(candles_15m) < 20 or current_price <= 0:
            return conditions
        
        ema20 = self._calculate_ema(candles_15m, 20)
        
        if ema20 > 0:
            deviation = (current_price - ema20) / ema20 * 100
            
            if abs(deviation) >= self.config.EMA_DEVIATION:
                conditions.append(FastTriggerCondition(
                    name="ema_deviation",
                    value=deviation,
                    threshold=self.config.EMA_DEVIATION,
                    direction="above" if deviation > 0 else "below",
                    urgency="medium",
                    description=f"价格偏离 EMA20: {deviation:+.2f}% ({'超买区' if deviation > 0 else '超卖区'})"
                ))
        
        return conditions
    
    # ========== 数据获取 ==========
    
    async def _fetch_ticker(self, session: aiohttp.ClientSession) -> Dict:
        """获取当前行情"""
        url = f"{self.base_url}/api/v5/market/ticker"
        params = {"instId": self.symbol}
        
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code") == "0" and result.get("data"):
                        return result["data"][0]
        except Exception as e:
            logger.debug(f"[FastMonitor] Ticker fetch error: {e}")
        
        return {}
    
    async def _fetch_candles(
        self,
        session: aiohttp.ClientSession,
        bar: str,
        limit: int
    ) -> List[Dict]:
        """获取 K 线数据"""
        url = f"{self.base_url}/api/v5/market/candles"
        params = {
            "instId": self.symbol,
            "bar": bar,
            "limit": str(limit)
        }
        
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code") == "0":
                        # OKX: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                        return [
                            {
                                "ts": int(c[0]),
                                "open": float(c[1]),
                                "high": float(c[2]),
                                "low": float(c[3]),
                                "close": float(c[4]),
                                "volume": float(c[5])
                            }
                            for c in result.get("data", [])
                        ]
        except Exception as e:
            logger.debug(f"[FastMonitor] Candles fetch error ({bar}): {e}")
        
        return []
    
    async def _fetch_funding_rate(self, session: aiohttp.ClientSession) -> Dict:
        """获取资金费率"""
        url = f"{self.base_url}/api/v5/public/funding-rate"
        params = {"instId": self.symbol}
        
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code") == "0" and result.get("data"):
                        return result["data"][0]
        except Exception as e:
            logger.debug(f"[FastMonitor] Funding rate fetch error: {e}")
        
        return {}
    
    async def _fetch_open_interest(self, session: aiohttp.ClientSession) -> Dict:
        """获取持仓量"""
        url = f"{self.base_url}/api/v5/public/open-interest"
        params = {"instId": self.symbol}
        
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code") == "0" and result.get("data"):
                        return result["data"][0]
        except Exception as e:
            logger.debug(f"[FastMonitor] Open interest fetch error: {e}")
        
        return {}
    
    # ========== 计算辅助函数 ==========
    
    def _calc_price_change(self, candles: List[Dict], periods: int = 1) -> float:
        """计算价格变化百分比"""
        if len(candles) < periods + 1:
            return 0.0
        
        current = candles[0].get("close", 0)
        prev = candles[periods].get("close", 0)
        
        if prev == 0:
            return 0.0
        
        return (current - prev) / prev * 100
    
    def _calculate_rsi(self, candles: List[Dict], period: int = 14) -> float:
        """计算 RSI"""
        if len(candles) < period + 1:
            return 50.0
        
        closes = [c.get("close", 0) for c in candles]
        closes.reverse()  # OKX 返回新到旧，反转
        
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def _calculate_ema(self, candles: List[Dict], period: int) -> float:
        """计算 EMA"""
        closes = [c.get("close", 0) for c in candles]
        closes.reverse()
        
        if len(closes) < period:
            return closes[-1] if closes else 0.0
        
        multiplier = 2 / (period + 1)
        ema = sum(closes[:period]) / period
        
        for i in range(period, len(closes)):
            ema = (closes[i] - ema) * multiplier + ema
        
        return ema
    
    def get_status(self) -> Dict:
        """获取监控器状态"""
        return {
            "symbol": self.symbol,
            "last_funding_rate": self._last_funding_rate,
            "last_open_interest": self._last_open_interest,
            "price_history_len": len(self._price_history),
            "config": {
                "price_spike_1m": self.config.PRICE_SPIKE_1M,
                "price_spike_5m": self.config.PRICE_SPIKE_5M,
                "volume_spike_5m": self.config.VOLUME_SPIKE_5M,
                "rsi_overbought": self.config.RSI_OVERBOUGHT,
                "rsi_oversold": self.config.RSI_OVERSOLD,
            }
        }


# ========== 测试入口 ==========
if __name__ == "__main__":
    async def test():
        monitor = FastMonitor()
        
        print("\n" + "="*50)
        print("FastMonitor Test")
        print("="*50)
        
        result = await monitor.check()
        
        print(f"\nShould Trigger: {result.should_trigger}")
        print(f"Urgency: {result.urgency}")
        print(f"Timestamp: {result.timestamp}")
        
        if result.conditions:
            print(f"\nTriggered Conditions ({len(result.conditions)}):")
            for cond in result.conditions:
                print(f"  - {cond.name}: {cond.value:.2f} (threshold: {cond.threshold})")
                print(f"    {cond.description}")
        else:
            print("\nNo conditions triggered - market is calm")
        
        print("\n" + "="*50)
        print("Monitor Status:")
        print(monitor.get_status())
    
    asyncio.run(test())
