"""
Unit Tests for Trading Models (TradingSignal, Position, etc.)

Tests cover:
- UM-001 to UM-008: TradingSignal creation and validation
- Position, TradeRecord, AgentVote models
"""

import pytest
import os
from datetime import datetime
from unittest.mock import patch

# Set environment variables before importing models
os.environ.setdefault('MAX_LEVERAGE', '20')
os.environ.setdefault('MIN_CONFIDENCE', '60')

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.models.trading_models import (
    TradingSignal,
    Position,
    TradeRecord,
    AccountBalance,
    AgentVote,
    RiskLimits,
    TradingConfig,
    MarketData,
)


# =============================================================================
# UM-001: TradingSignal Creation
# =============================================================================

class TestTradingSignalCreation:
    """Test TradingSignal model creation"""
    
    def test_full_creation(self):
        """UM-001: Create TradingSignal with all fields"""
        signal = TradingSignal(
            direction="long",
            symbol="BTC-USDT-SWAP",
            leverage=3,
            amount_percent=0.2,
            entry_price=94500.50,
            take_profit_price=103950.55,
            stop_loss_price=90720.48,
            confidence=65,
            reasoning="All experts recommend LONG based on technical breakout.",
            leader_summary="Consensus: Bullish with TP 10%, SL 4%",
            agents_consensus={"TechnicalAnalyst": "long", "SentimentAnalyst": "long"},
        )
        
        assert signal.direction == "long"
        assert signal.symbol == "BTC-USDT-SWAP"
        assert signal.leverage == 3
        assert signal.amount_percent == 0.2
        assert signal.entry_price == 94500.50
        assert signal.take_profit_price == 103950.55
        assert signal.stop_loss_price == 90720.48
        assert signal.confidence == 65
        assert len(signal.agents_consensus) == 2


# =============================================================================
# UM-002 to UM-004: Direction Types
# =============================================================================

class TestTradingSignalDirections:
    """Test different direction types"""
    
    def test_hold_signal(self):
        """UM-002: Create HOLD signal"""
        signal = TradingSignal(
            direction="hold",
            entry_price=94500.0,
            take_profit_price=94500.0,
            stop_loss_price=94500.0,
            confidence=50,
            reasoning="Market uncertainty"
        )
        
        assert signal.direction == "hold"
        assert signal.amount_percent == 0.1  # default
    
    def test_long_signal(self):
        """UM-003: Create LONG signal"""
        signal = TradingSignal(
            direction="long",
            entry_price=94500.0,
            take_profit_price=103950.0,  # TP > entry for long
            stop_loss_price=90720.0,     # SL < entry for long
            confidence=70,
            reasoning="Bullish trend"
        )
        
        assert signal.direction == "long"
        assert signal.take_profit_price > signal.entry_price
        assert signal.stop_loss_price < signal.entry_price
    
    def test_short_signal(self):
        """UM-004: Create SHORT signal"""
        signal = TradingSignal(
            direction="short",
            entry_price=94500.0,
            take_profit_price=85050.0,   # TP < entry for short
            stop_loss_price=99225.0,     # SL > entry for short
            confidence=70,
            reasoning="Bearish trend"
        )
        
        assert signal.direction == "short"
        assert signal.take_profit_price < signal.entry_price
        assert signal.stop_loss_price > signal.entry_price


# =============================================================================
# UM-005: Leverage Validation
# =============================================================================

class TestLeverageValidation:
    """Test leverage validation against MAX_LEVERAGE"""
    
    def test_valid_leverage(self):
        """UM-005a: Valid leverage within limit"""
        signal = TradingSignal(
            direction="long",
            leverage=10,  # Within limit (MAX_LEVERAGE=20)
            entry_price=94500.0,
            take_profit_price=103950.0,
            stop_loss_price=90720.0,
            confidence=70,
            reasoning="Test"
        )
        assert signal.leverage == 10
    
    def test_leverage_at_max(self):
        """UM-005b: Leverage at MAX_LEVERAGE"""
        # Set MAX_LEVERAGE to 20
        with patch.dict(os.environ, {'MAX_LEVERAGE': '20'}):
            signal = TradingSignal(
                direction="long",
                leverage=20,  # At max
                entry_price=94500.0,
                take_profit_price=103950.0,
                stop_loss_price=90720.0,
                confidence=70,
                reasoning="Test"
            )
            assert signal.leverage == 20
    
    def test_leverage_exceeds_max(self):
        """UM-005c: Leverage exceeds MAX_LEVERAGE raises error"""
        with patch.dict(os.environ, {'MAX_LEVERAGE': '20'}):
            from pydantic import ValidationError
            with pytest.raises(ValidationError) as exc_info:
                TradingSignal(
                    direction="long",
                    leverage=25,  # Exceeds limit
                    entry_price=94500.0,
                    take_profit_price=103950.0,
                    stop_loss_price=90720.0,
                    confidence=70,
                    reasoning="Test"
                )
            assert "leverage" in str(exc_info.value).lower()


# =============================================================================
# UM-006: Confidence Range
# =============================================================================

class TestConfidenceValidation:
    """Test confidence range validation"""
    
    def test_confidence_zero(self):
        """UM-006a: Confidence at 0"""
        signal = TradingSignal(
            direction="hold",
            confidence=0,
            entry_price=94500.0,
            take_profit_price=94500.0,
            stop_loss_price=94500.0,
            reasoning="Fallback"
        )
        assert signal.confidence == 0
    
    def test_confidence_100(self):
        """UM-006b: Confidence at 100"""
        signal = TradingSignal(
            direction="long",
            confidence=100,
            entry_price=94500.0,
            take_profit_price=103950.0,
            stop_loss_price=90720.0,
            reasoning="Very confident"
        )
        assert signal.confidence == 100
    
    def test_confidence_negative(self):
        """UM-006c: Negative confidence raises error"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            TradingSignal(
                direction="long",
                confidence=-10,
                entry_price=94500.0,
                take_profit_price=103950.0,
                stop_loss_price=90720.0,
                reasoning="Test"
            )
        assert "confidence" in str(exc_info.value).lower()
    
    def test_confidence_over_100(self):
        """UM-006d: Confidence over 100 raises error"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            TradingSignal(
                direction="long",
                confidence=150,
                entry_price=94500.0,
                take_profit_price=103950.0,
                stop_loss_price=90720.0,
                reasoning="Test"
            )
        assert "confidence" in str(exc_info.value).lower()


# =============================================================================
# UM-007: Risk Reward Ratio
# =============================================================================

class TestRiskRewardRatio:
    """Test risk/reward ratio calculation"""
    
    def test_rrr_long_position(self):
        """UM-007a: Calculate RRR for long position"""
        signal = TradingSignal(
            direction="long",
            entry_price=100.0,
            take_profit_price=110.0,  # +10 reward
            stop_loss_price=95.0,     # -5 risk
            confidence=70,
            reasoning="Test"
        )
        
        # Reward: 110 - 100 = 10
        # Risk: 100 - 95 = 5
        # RRR: 10 / 5 = 2.0
        assert signal.risk_reward_ratio == 2.0
    
    def test_rrr_short_position(self):
        """UM-007b: Calculate RRR for short position"""
        signal = TradingSignal(
            direction="short",
            entry_price=100.0,
            take_profit_price=90.0,   # +10 reward
            stop_loss_price=105.0,    # -5 risk
            confidence=70,
            reasoning="Test"
        )
        
        # Reward: 100 - 90 = 10
        # Risk: 105 - 100 = 5
        # RRR: 10 / 5 = 2.0
        assert signal.risk_reward_ratio == 2.0
    
    def test_rrr_hold_is_zero(self):
        """UM-007c: RRR for hold is 0"""
        signal = TradingSignal(
            direction="hold",
            entry_price=100.0,
            take_profit_price=100.0,
            stop_loss_price=100.0,
            confidence=50,
            reasoning="Test"
        )
        
        assert signal.risk_reward_ratio == 0.0


# =============================================================================
# UM-008: Timestamp Default
# =============================================================================

class TestTimestampDefault:
    """Test timestamp default behavior"""
    
    def test_timestamp_default(self):
        """UM-008: Default timestamp uses datetime.now()"""
        before = datetime.now()
        
        signal = TradingSignal(
            direction="hold",
            entry_price=94500.0,
            take_profit_price=94500.0,
            stop_loss_price=94500.0,
            confidence=50,
            reasoning="Test"
        )
        
        after = datetime.now()
        
        assert signal.timestamp >= before
        assert signal.timestamp <= after


# =============================================================================
# Additional Model Tests
# =============================================================================

class TestAgentVote:
    """Test AgentVote model"""
    
    def test_agent_vote_creation(self):
        """Create AgentVote with all fields"""
        vote = AgentVote(
            agent_id="tech_analyst",
            agent_name="TechnicalAnalyst",
            direction="long",
            confidence=75,
            reasoning="RSI oversold, bullish divergence",
            suggested_leverage=5,
            suggested_tp_percent=10.0,
            suggested_sl_percent=4.0
        )
        
        assert vote.agent_id == "tech_analyst"
        assert vote.direction == "long"
        assert vote.confidence == 75
        assert vote.suggested_leverage == 5


class TestPosition:
    """Test Position model"""
    
    def test_position_creation(self):
        """Create Position with all fields"""
        position = Position(
            symbol="BTC-USDT-SWAP",
            direction="long",
            size=0.1,
            entry_price=94500.0,
            current_price=95000.0,
            leverage=3,
            unrealized_pnl=50.0,
            unrealized_pnl_percent=0.53,
            take_profit_price=103950.0,
            stop_loss_price=90720.0,
            margin=1000.0,
            liquidation_price=85000.0,
            opened_at=datetime.now()
        )
        
        assert position.symbol == "BTC-USDT-SWAP"
        assert position.direction == "long"
        assert position.size == 0.1
        assert position.leverage == 3


class TestRiskLimits:
    """Test RiskLimits model"""
    
    def test_risk_limits_defaults(self):
        """Test RiskLimits defaults from environment"""
        limits = RiskLimits()
        
        # Should read from environment or use defaults
        assert limits.max_leverage >= 1
        assert limits.max_position_percent > 0
        assert limits.min_confidence >= 0


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
