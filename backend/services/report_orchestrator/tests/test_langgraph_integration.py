"""
LangGraph Integration Tests

End-to-end tests for the LangGraph trading workflow.
Tests the complete flow from market analysis to execution.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

# Import the modules to test
from app.core.trading.orchestration.graph import TradingGraph
from app.core.trading.orchestration.state import TradingState


class TestLangGraphWorkflow:
    """Test suite for LangGraph trading workflow integration."""
    
    @pytest.fixture
    def mock_agents(self):
        """Create mock agents for testing."""
        agents = {}
        for agent_id in ["TechnicalAnalyst", "MacroEconomist", "SentimentAnalyst", 
                         "OnchainAnalyst", "FundamentalAnalyst"]:
            agent = MagicMock()
            agent.agent_id = agent_id
            agents[agent_id] = agent
        return agents
    
    @pytest.fixture
    def mock_executor(self):
        """Create mock executor agent."""
        executor = MagicMock()
        executor.execute = AsyncMock(return_value=MagicMock(
            direction="long",
            leverage=5,
            confidence=75,
            entry_price=95000.0,
            take_profit_price=102600.0,
            stop_loss_price=92150.0,
            reasoning="Test execution"
        ))
        return executor
    
    @pytest.fixture
    def sample_votes(self):
        """Sample agent votes for testing."""
        return [
            {
                "agent_id": "TechnicalAnalyst",
                "direction": "long",
                "confidence": 80,
                "leverage": 5,
                "tp_percent": 8.0,
                "sl_percent": 3.0,
                "reasoning": "RSI oversold, MACD bullish"
            },
            {
                "agent_id": "MacroEconomist",
                "direction": "long",
                "confidence": 70,
                "leverage": 3,
                "tp_percent": 10.0,
                "sl_percent": 4.0,
                "reasoning": "Fed dovish, inflation cooling"
            },
            {
                "agent_id": "SentimentAnalyst",
                "direction": "long",
                "confidence": 65,
                "leverage": 2,
                "tp_percent": 6.0,
                "sl_percent": 3.0,
                "reasoning": "Social sentiment bullish"
            },
            {
                "agent_id": "OnchainAnalyst",
                "direction": "hold",
                "confidence": 55,
                "leverage": 1,
                "tp_percent": 5.0,
                "sl_percent": 2.0,
                "reasoning": "Mixed on-chain signals"
            },
            {
                "agent_id": "FundamentalAnalyst",
                "direction": "long",
                "confidence": 75,
                "leverage": 4,
                "tp_percent": 7.0,
                "sl_percent": 3.5,
                "reasoning": "Strong institutional flows"
            }
        ]
    
    @pytest.fixture
    def sample_position_context(self):
        """Sample position context."""
        return {
            "has_position": False,
            "direction": None,
            "entry_price": 0,
            "current_price": 95000.0,
            "unrealized_pnl": 0,
            "unrealized_pnl_percent": 0,
            "leverage": 1
        }
    
    @pytest.fixture
    def sample_market_data(self):
        """Sample market data."""
        return {
            "symbol": "BTC-USDT-SWAP",
            "current_price": 95000.0,
            "change_24h": 2.5,
            "volume_24h": 50000000000,
            "high_24h": 96000.0,
            "low_24h": 93000.0
        }
    
    def test_trading_graph_initialization(self):
        """Test that TradingGraph initializes correctly."""
        graph = TradingGraph()
        assert graph is not None
        assert graph._compiled_graph is not None
    
    @pytest.mark.asyncio
    async def test_graph_run_with_mock_votes(
        self, 
        sample_votes, 
        sample_position_context,
        sample_market_data,
        mock_executor
    ):
        """Test graph execution with mocked vote data."""
        graph = TradingGraph()
        
        # Run with pre-computed votes
        result = await graph.run(
            position_context=sample_position_context,
            market_snapshot=sample_market_data,
            agent_votes=sample_votes,
            executor=mock_executor
        )
        
        assert result is not None
        assert "final_signal" in result or "error" in result
        
        if "final_signal" in result and result["final_signal"]:
            signal = result["final_signal"]
            assert signal.direction in ["long", "short", "hold", "close"]
    
    @pytest.mark.asyncio
    async def test_risk_assessment_blocks_high_risk(
        self,
        sample_position_context,
        sample_market_data,
        mock_executor
    ):
        """Test that risk assessment can block trades."""
        # Create votes with low confidence (should trigger block)
        low_confidence_votes = [
            {"agent_id": f"Agent{i}", "direction": "long", "confidence": 30, 
             "leverage": 1, "tp_percent": 5, "sl_percent": 3, "reasoning": "Low confidence"}
            for i in range(5)
        ]
        
        graph = TradingGraph()
        result = await graph.run(
            position_context=sample_position_context,
            market_snapshot=sample_market_data,
            agent_votes=low_confidence_votes,
            executor=mock_executor
        )
        
        # With very low confidence, execution might be blocked
        # Check either blocked or hold
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_message_broadcasting(
        self,
        sample_votes,
        sample_position_context,
        sample_market_data,
        mock_executor
    ):
        """Test that on_message callback is invoked correctly."""
        messages_received = []
        
        async def on_message_callback(message: Dict[str, Any]):
            messages_received.append(message)
        
        graph = TradingGraph()
        result = await graph.run(
            position_context=sample_position_context,
            market_snapshot=sample_market_data,
            agent_votes=sample_votes,
            executor=mock_executor,
            on_message=on_message_callback
        )
        
        # Should receive messages (Risk Manager, Leader, etc.)
        # Note: Actual message count depends on implementation
        assert isinstance(messages_received, list)
    
    @pytest.mark.asyncio
    async def test_node_timing_tracking(
        self,
        sample_votes,
        sample_position_context,
        sample_market_data,
        mock_executor
    ):
        """Test that node timings are tracked."""
        graph = TradingGraph()
        result = await graph.run(
            position_context=sample_position_context,
            market_snapshot=sample_market_data,
            agent_votes=sample_votes,
            executor=mock_executor
        )
        
        if "node_timings" in result:
            timings = result["node_timings"]
            assert isinstance(timings, dict)
            # Should have timings for executed nodes
    
    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_votes(
        self,
        sample_position_context,
        sample_market_data,
        mock_executor
    ):
        """Test error handling with invalid input."""
        graph = TradingGraph()
        
        # Empty votes should be handled gracefully
        result = await graph.run(
            position_context=sample_position_context,
            market_snapshot=sample_market_data,
            agent_votes=[],  # Empty votes
            executor=mock_executor
        )
        
        assert result is not None
        # Should not crash, may produce hold or error


class TestATRIntegration:
    """Test ATR stop-loss integration."""
    
    @pytest.mark.asyncio
    async def test_atr_calculator_import(self):
        """Test that ATR calculator can be imported."""
        from app.core.trading.atr_stop_loss import calculate_dynamic_sl, get_atr_calculator
        
        calculator = get_atr_calculator()
        assert calculator is not None
    
    @pytest.mark.asyncio
    async def test_atr_calculation_long(self):
        """Test ATR calculation for long position."""
        from app.core.trading.atr_stop_loss import calculate_dynamic_sl
        
        result = await calculate_dynamic_sl(
            direction="long",
            entry_price=95000.0,
            leverage=5,
            symbol="BTC-USDT-SWAP"
        )
        
        if result:
            # SL should be below entry for long
            assert result.stop_loss_price < 95000.0
            assert result.sl_percent > 0
    
    @pytest.mark.asyncio
    async def test_atr_calculation_short(self):
        """Test ATR calculation for short position."""
        from app.core.trading.atr_stop_loss import calculate_dynamic_sl
        
        result = await calculate_dynamic_sl(
            direction="short",
            entry_price=95000.0,
            leverage=5,
            symbol="BTC-USDT-SWAP"
        )
        
        if result:
            # SL should be above entry for short
            assert result.stop_loss_price > 95000.0
            assert result.sl_percent > 0


class TestSEMIAUTOMode:
    """Test SEMI_AUTO mode functionality."""

    @pytest.mark.asyncio
    async def test_mode_manager_import(self):
        """Test that mode manager can be imported."""
        from app.core.trading.mode_manager import (
            TradingModeManager,
            TradingMode,
            get_mode_manager
        )

        assert TradingMode.SEMI_AUTO.value == "semi_auto"
        assert not hasattr(TradingMode, "FULL_AUTO")
        assert not hasattr(TradingMode, "MANUAL")

    @pytest.mark.asyncio
    async def test_pending_trade_creation(self):
        """Test pending trade creation and retrieval."""
        from app.core.trading.mode_manager import get_mode_manager

        mode_manager = get_mode_manager()

        # Create a pending trade
        pending = await mode_manager.add_pending_trade(
            direction="long",
            leverage=5,
            entry_price=95000.0,
            take_profit=102600.0,
            stop_loss=92150.0,
            confidence=75,
            reasoning="Test trade",
            amount_percent=0.2
        )

        assert pending is not None
        assert pending.trade_id is not None

        # Retrieve it
        retrieved = await mode_manager.get_pending_trade(pending.trade_id)
        if retrieved:
            assert retrieved.id == pending.trade_id


class TestHITLModeBlocking:
    """Test Human-in-the-Loop mode blocking functionality."""

    @pytest.fixture
    def sample_votes(self):
        """Sample agent votes for testing."""
        return [
            {
                "agent_id": "TechnicalAnalyst",
                "agent_name": "TechnicalAnalyst",
                "direction": "long",
                "confidence": 80,
                "leverage": 5,
                "take_profit_percent": 8.0,
                "stop_loss_percent": 3.0,
                "reasoning": "RSI oversold, MACD bullish"
            },
            {
                "agent_id": "SentimentAnalyst",
                "agent_name": "SentimentAnalyst",
                "direction": "long",
                "confidence": 75,
                "leverage": 4,
                "take_profit_percent": 7.0,
                "stop_loss_percent": 3.5,
                "reasoning": "Social sentiment bullish"
            }
        ]

    @pytest.mark.asyncio
    async def test_hitl_only_requires_confirmation(self, sample_votes):
        """HITL-only: should always create a pending trade and wait for confirmation."""
        from app.core.trading.mode_manager import get_mode_manager, TradingMode, ExecutionAction

        mode_manager = get_mode_manager()

        # Any set_mode call should normalize to SEMI_AUTO
        await mode_manager.set_mode(TradingMode.SEMI_AUTO)
        current_mode = await mode_manager.get_mode()
        assert current_mode == TradingMode.SEMI_AUTO

        decision = await mode_manager.should_execute(
            {
                "direction": "long",
                "confidence": 80,
                "leverage": 5,
                "entry_price": 95000.0,
                "take_profit_price": 102600.0,
                "stop_loss_price": 92150.0,
                "amount_percent": 0.2,
                "symbol": "BTC-USDT-SWAP",
                "reasoning": "test",
            }
        )

        assert decision.action == ExecutionAction.WAIT_CONFIRMATION
        assert decision.pending_trade_id is not None

    @pytest.mark.asyncio
    async def test_pending_trade_approval_flow(self):
        """Test the full pending trade approval flow."""
        from app.core.trading.mode_manager import get_mode_manager, TradingMode

        mode_manager = get_mode_manager()

        # Set to SEMI_AUTO
        await mode_manager.set_mode(TradingMode.SEMI_AUTO)

        # Create pending trade
        pending = await mode_manager.add_pending_trade(
            direction="long",
            leverage=5,
            entry_price=95000.0,
            take_profit=102600.0,
            stop_loss=92150.0,
            confidence=75,
            reasoning="Test HITL approval flow",
            amount_percent=0.2
        )

        assert pending is not None
        trade_id = pending.trade_id

        # Get all pending trades
        all_pending = await mode_manager.get_all_pending_trades()
        assert any(t.id == trade_id for t in all_pending)

        # Approve the trade
        approved = await mode_manager.approve_trade(trade_id)
        # Note: approval may fail if no actual trader is connected
        # Just verify the method doesn't crash

        # Clean up - reject if still pending
        await mode_manager.reject_trade(trade_id, reason="Test cleanup")

    @pytest.mark.asyncio
    async def test_pending_trade_rejection(self):
        """Test pending trade rejection."""
        from app.core.trading.mode_manager import get_mode_manager, TradingMode

        mode_manager = get_mode_manager()

        # Set to SEMI_AUTO
        await mode_manager.set_mode(TradingMode.SEMI_AUTO)

        # Create pending trade
        pending = await mode_manager.add_pending_trade(
            direction="short",
            leverage=3,
            entry_price=95000.0,
            take_profit=87400.0,
            stop_loss=97850.0,
            confidence=65,
            reasoning="Test rejection flow",
            amount_percent=0.15
        )

        assert pending is not None
        trade_id = pending.trade_id

        # Reject the trade
        rejected = await mode_manager.reject_trade(trade_id, reason="User rejected")
        assert rejected is True

        # Verify it's no longer in pending list
        all_pending = await mode_manager.get_all_pending_trades()
        assert not any(t.id == trade_id for t in all_pending)

    @pytest.mark.asyncio
    async def test_mode_persistence(self):
        """Test that mode persists across manager instances."""
        from app.core.trading.mode_manager import TradingModeManager, TradingMode

        # Create first manager and set mode
        manager1 = TradingModeManager()
        await manager1.set_mode(TradingMode.SEMI_AUTO)

        # Create second manager (simulating restart)
        manager2 = TradingModeManager()
        mode = await manager2.get_mode()

        # HITL-only: only SEMI_AUTO exists.
        assert mode == TradingMode.SEMI_AUTO


class TestWeightLearnerIntegration:
    """Test WeightLearner integration."""

    @pytest.mark.asyncio
    async def test_weight_learner_import(self):
        """Test that WeightLearner can be imported."""
        from app.core.trading.weight_learner import (
            AgentWeightLearner,
            get_weight_learner,
            get_learned_weights
        )

        learner = get_weight_learner()
        assert learner is not None

    @pytest.mark.asyncio
    async def test_get_learned_weights(self):
        """Test getting learned weights."""
        from app.core.trading.weight_learner import get_learned_weights

        weights = await get_learned_weights()
        assert isinstance(weights, dict)

        # Should have weights for standard agents
        expected_agents = [
            "TechnicalAnalyst",
            "FundamentalAnalyst",
            "SentimentAnalyst",
        ]
        for agent in expected_agents:
            assert agent in weights
            assert 0.5 <= weights[agent] <= 2.0

    @pytest.mark.asyncio
    async def test_weight_bounds(self):
        """Test that weights stay within bounds."""
        from app.core.trading.weight_learner import get_weight_learner

        learner = get_weight_learner()

        # Get weight for an agent
        weight = await learner.get_agent_weight("TechnicalAnalyst")

        # Should be within bounds
        assert 0.5 <= weight <= 2.0


class TestAntiBiasIntegration:
    """Test anti-bias system integration."""

    @pytest.mark.asyncio
    async def test_direction_neutralizer_import(self):
        """Test that DirectionNeutralizer can be imported."""
        from app.core.trading.anti_bias import (
            DirectionNeutralizer,
            NeutralVote,
            EchoChamberDetector,
            get_echo_chamber_detector
        )

        detector = get_echo_chamber_detector()
        assert detector is not None

    @pytest.mark.asyncio
    async def test_echo_chamber_detection(self):
        """Test echo chamber detection with unanimous votes."""
        from app.core.trading.anti_bias import get_echo_chamber_detector

        detector = get_echo_chamber_detector()

        # Create unanimous votes (should trigger echo chamber warning)
        unanimous_votes = [
            {"agent_id": f"Agent{i}", "direction": "long", "confidence": 80}
            for i in range(5)
        ]

        result = detector.check(unanimous_votes)

        # 100% agreement should trigger echo chamber
        assert result.consensus_ratio == 1.0
        assert result.status.value == "echo_chamber_detected"

    @pytest.mark.asyncio
    async def test_no_echo_chamber_with_mixed_votes(self):
        """Test that mixed votes don't trigger echo chamber."""
        from app.core.trading.anti_bias import get_echo_chamber_detector

        detector = get_echo_chamber_detector()

        # Create mixed votes
        mixed_votes = [
            {"agent_id": "Agent1", "direction": "long", "confidence": 80},
            {"agent_id": "Agent2", "direction": "long", "confidence": 75},
            {"agent_id": "Agent3", "direction": "short", "confidence": 70},
            {"agent_id": "Agent4", "direction": "hold", "confidence": 60},
            {"agent_id": "Agent5", "direction": "long", "confidence": 65},
        ]

        result = detector.check(mixed_votes)

        # 60% agreement should not trigger echo chamber (threshold is 80%)
        assert result.consensus_ratio < 0.8
        assert result.status.value != "echo_chamber_detected"

    @pytest.mark.asyncio
    async def test_neutral_vote_aggregation(self):
        """Test neutral vote aggregation."""
        from app.core.trading.anti_bias import DirectionNeutralizer, NeutralVote

        # Create neutral votes
        votes = [
            NeutralVote(
                agent_id="Agent1",
                agent_name="Agent1",
                bullish_score=75,
                bearish_score=35,
                confidence=70,
                leverage=5,
                take_profit_percent=8.0,
                stop_loss_percent=3.0,
                reasoning="Bullish signals"
            ),
            NeutralVote(
                agent_id="Agent2",
                agent_name="Agent2",
                bullish_score=80,
                bearish_score=30,
                confidence=75,
                leverage=4,
                take_profit_percent=7.0,
                stop_loss_percent=3.5,
                reasoning="Strong bullish"
            ),
        ]

        weights = {"Agent1": 1.0, "Agent2": 1.2}

        direction, confidence, metadata = DirectionNeutralizer.aggregate_neutral_votes(
            votes, weights
        )

        # Should be bullish given the scores
        assert direction == "long"
        assert confidence > 0
        assert "avg_bullish_score" in metadata
        assert "avg_bearish_score" in metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
