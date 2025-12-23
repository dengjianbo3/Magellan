"""
Technical Analysis Models
技术分析数据模型

用于技术分析Agent的输入输出数据结构定义
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class TrendDirection(str, Enum):
    """趋势方向"""
    STRONG_BULLISH = "strong_bullish"    # 强势上涨
    BULLISH = "bullish"                   # 上涨
    NEUTRAL = "neutral"                   # 横盘震荡
    BEARISH = "bearish"                   # 下跌
    STRONG_BEARISH = "strong_bearish"    # 强势下跌


class SignalStrength(str, Enum):
    """信号强度"""
    STRONG_BUY = "strong_buy"      # 强烈买入
    BUY = "buy"                     # 买入
    NEUTRAL = "neutral"             # 中性
    SELL = "sell"                   # 卖出
    STRONG_SELL = "strong_sell"    # 强烈卖出


class TrendStrength(str, Enum):
    """趋势强度 (基于ADX)"""
    VERY_STRONG = "very_strong"    # ADX > 50
    STRONG = "strong"              # ADX 25-50
    MODERATE = "moderate"          # ADX 20-25
    WEAK = "weak"                  # ADX < 20


class EMAAlignment(str, Enum):
    """均线排列状态"""
    BULLISH_ALIGNMENT = "bullish_alignment"    # 多头排列
    BEARISH_ALIGNMENT = "bearish_alignment"    # 空头排列
    MIXED = "mixed"                             # 纠缠


class MarketType(str, Enum):
    """市场类型"""
    CRYPTO = "crypto"    # 加密货币
    STOCK = "stock"      # 股票
    FOREX = "forex"      # 外汇
    INDEX = "index"      # 指数


class Timeframe(str, Enum):
    """时间周期"""
    M1 = "1m"      # 1分钟
    M5 = "5m"      # 5分钟
    M15 = "15m"    # 15分钟
    M30 = "30m"    # 30分钟
    H1 = "1h"      # 1小时
    H4 = "4h"      # 4小时
    D1 = "1d"      # 日线
    W1 = "1w"      # 周线
    MN = "1M"      # 月线


# ==================== 指标信号模型 ====================

class IndicatorSignal(BaseModel):
    """单个指标信号"""
    name: str = Field(..., description="指标名称")
    value: float = Field(..., description="当前值")
    signal: SignalStrength = Field(..., description="交易信号")
    description: str = Field(..., description="解读说明")

    class Config:
        use_enum_values = True


class RSIIndicator(BaseModel):
    """RSI指标"""
    value: float = Field(..., ge=0, le=100, description="RSI值")
    signal: SignalStrength
    period: int = Field(default=14, description="计算周期")
    description: str


class MACDIndicator(BaseModel):
    """MACD指标"""
    macd: float = Field(..., description="MACD线")
    signal_line: float = Field(..., description="信号线")
    histogram: float = Field(..., description="柱状图")
    signal: SignalStrength
    description: str


class BollingerBandsIndicator(BaseModel):
    """布林带指标"""
    upper: float = Field(..., description="上轨")
    middle: float = Field(..., description="中轨")
    lower: float = Field(..., description="下轨")
    width: float = Field(..., description="带宽百分比")
    position: str = Field(..., description="价格位置")
    signal: SignalStrength
    description: str


class EMAIndicator(BaseModel):
    """均线指标"""
    ema_7: float = Field(..., description="EMA7")
    ema_25: float = Field(..., description="EMA25")
    ema_99: float = Field(..., description="EMA99")
    alignment: EMAAlignment = Field(..., description="排列状态")
    signal: SignalStrength
    description: str

    class Config:
        use_enum_values = True


class KDJIndicator(BaseModel):
    """KDJ指标"""
    k: float = Field(..., description="K值")
    d: float = Field(..., description="D值")
    j: float = Field(..., description="J值")
    signal: SignalStrength
    description: str


class ADXIndicator(BaseModel):
    """ADX指标"""
    value: float = Field(..., ge=0, description="ADX值")
    trend_strength: TrendStrength
    description: str

    class Config:
        use_enum_values = True


# ==================== 分析结果模型 ====================

class TrendAnalysis(BaseModel):
    """趋势分析结果"""
    direction: TrendDirection = Field(..., description="趋势方向")
    strength: float = Field(..., ge=0, le=1, description="趋势强度 0-1")
    ema_alignment: EMAAlignment = Field(..., description="均线排列")
    adx_value: Optional[float] = Field(None, description="ADX值")
    description: str = Field(..., description="趋势描述")

    class Config:
        use_enum_values = True


class SupportResistance(BaseModel):
    """支撑阻力位"""
    current_price: float = Field(..., description="当前价格")
    support_levels: List[float] = Field(..., description="支撑位列表")
    resistance_levels: List[float] = Field(..., description="阻力位列表")
    nearest_support: float = Field(..., description="最近支撑位")
    nearest_resistance: float = Field(..., description="最近阻力位")
    method: str = Field(..., description="计算方法 (fibonacci/pivot)")


class CandlestickPattern(BaseModel):
    """K线形态"""
    name: str = Field(..., description="形态名称(中文)")
    english_name: str = Field(..., description="形态名称(英文)")
    type: str = Field(..., description="形态类型 (reversal/continuation)")
    direction: str = Field(..., description="方向 (bullish/bearish)")
    strength: str = Field(..., description="强度 (strong/medium/weak)")


class PatternRecognition(BaseModel):
    """K线形态识别结果"""
    patterns_found: List[CandlestickPattern] = Field(default_factory=list, description="识别到的形态")
    dominant_pattern: Optional[str] = Field(None, description="主导形态")
    pattern_signal: SignalStrength = Field(default=SignalStrength.NEUTRAL, description="形态信号")

    class Config:
        use_enum_values = True


class TradingSuggestion(BaseModel):
    """交易建议"""
    action: SignalStrength = Field(..., description="建议操作")
    entry_zone: Optional[str] = Field(None, description="入场区间")
    stop_loss: Optional[float] = Field(None, description="止损位")
    take_profit_levels: Optional[List[float]] = Field(None, description="止盈位")
    risk_reward_ratio: Optional[float] = Field(None, description="风险收益比")
    reasoning: str = Field(..., description="建议理由")

    class Config:
        use_enum_values = True


# ==================== 完整输出模型 ====================

class TechnicalIndicators(BaseModel):
    """所有技术指标汇总"""
    rsi: Optional[RSIIndicator] = None
    macd: Optional[MACDIndicator] = None
    bollinger_bands: Optional[BollingerBandsIndicator] = None
    ema: Optional[EMAIndicator] = None
    kdj: Optional[KDJIndicator] = None
    adx: Optional[ADXIndicator] = None


class TechnicalAnalysisOutput(BaseModel):
    """技术分析完整输出"""

    # 基本信息
    symbol: str = Field(..., description="交易对")
    timeframe: str = Field(..., description="时间周期")
    market_type: MarketType = Field(default=MarketType.CRYPTO, description="市场类型")
    timestamp: str = Field(..., description="分析时间")

    # 价格信息
    current_price: float = Field(..., description="当前价格")
    price_change_24h: Optional[float] = Field(None, description="24小时涨跌幅%")

    # 综合评分
    technical_score: float = Field(..., ge=0, le=100, description="技术面综合评分")
    overall_signal: SignalStrength = Field(..., description="综合信号")
    confidence: float = Field(..., ge=0, le=1, description="置信度")

    # 趋势分析
    trend_analysis: TrendAnalysis = Field(..., description="趋势分析")

    # 技术指标
    indicators: TechnicalIndicators = Field(..., description="技术指标")
    indicator_signals: List[IndicatorSignal] = Field(default_factory=list, description="指标信号列表")

    # 支撑阻力
    support_resistance: SupportResistance = Field(..., description="支撑阻力位")

    # 形态识别
    pattern_recognition: PatternRecognition = Field(..., description="K线形态识别")

    # 交易建议
    trading_suggestion: TradingSuggestion = Field(..., description="交易建议")

    # 风险提示
    risk_warning: str = Field(..., description="风险提示")

    # 原始数据 (可选)
    raw_data: Optional[Dict[str, Any]] = Field(None, description="原始计算数据")

    class Config:
        use_enum_values = True


# ==================== Agent输入模型 ====================

class TechnicalAnalysisInput(BaseModel):
    """技术分析Agent输入"""
    symbol: str = Field(..., description="交易对 (如: BTC/USDT, AAPL)")
    timeframe: str = Field(default="1d", description="时间周期")
    market_type: str = Field(default="crypto", description="市场类型")
    indicators: Optional[List[str]] = Field(
        default=None,
        description="需要计算的指标列表，默认全部"
    )
    include_patterns: bool = Field(default=True, description="是否识别K线形态")
    quick_mode: bool = Field(default=False, description="快速模式(减少指标)")


# ==================== 辅助函数 ====================

def signal_to_score(signal: SignalStrength) -> float:
    """将信号转换为分数 (0-100)"""
    mapping = {
        SignalStrength.STRONG_BUY: 90,
        SignalStrength.BUY: 70,
        SignalStrength.NEUTRAL: 50,
        SignalStrength.SELL: 30,
        SignalStrength.STRONG_SELL: 10,
    }
    return mapping.get(signal, 50)


def score_to_signal(score: float) -> SignalStrength:
    """将分数转换为信号"""
    if score >= 80:
        return SignalStrength.STRONG_BUY
    elif score >= 60:
        return SignalStrength.BUY
    elif score >= 40:
        return SignalStrength.NEUTRAL
    elif score >= 20:
        return SignalStrength.SELL
    else:
        return SignalStrength.STRONG_SELL
