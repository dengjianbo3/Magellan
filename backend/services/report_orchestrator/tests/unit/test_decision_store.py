"""
Unit Tests for TradingDecision and TradingDecisionStore

Tests cover:
- DS-001 to DS-010: TradingDecision creation, serialization, deserialization
- Store operations: save, get, list recent decisions
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


# =============================================================================
# Mock Redis Module (needed before importing decision_store)
# =============================================================================

def setup_redis_mock():
    """Setup mock redis module"""
    import types
    redis_mock = types.ModuleType('redis')
    redis_mock.asyncio = types.ModuleType('redis.asyncio')
    
    class FakeRedis:
        def __init__(self):
            self._data = {}
            self._lists = {}
        
        async def ping(self):
            return True
        
        async def set(self, key, value, ex=None):
            self._data[key] = value
            return True
        
        async def get(self, key):
            return self._data.get(key)
        
        async def lpush(self, key, value):
            if key not in self._lists:
                self._lists[key] = []
            self._lists[key].insert(0, value)
            return len(self._lists[key])
        
        async def ltrim(self, key, start, end):
            if key in self._lists:
                self._lists[key] = self._lists[key][start:end+1]
            return True
        
        async def lrange(self, key, start, end):
            if key not in self._lists:
                return []
            return self._lists[key][start:end+1]
        
        async def close(self):
            pass
    
    redis_mock.asyncio.from_url = lambda *a, **k: FakeRedis()
    redis_mock.asyncio.FakeRedis = FakeRedis
    
    sys.modules['redis'] = redis_mock
    sys.modules['redis.asyncio'] = redis_mock.asyncio
    return redis_mock, FakeRedis


# Setup once at module level
_redis_mock, FakeRedis = setup_redis_mock()

# Now import the module under test
from app.core.trading.decision_store import TradingDecision, TradingDecisionStore


# =============================================================================
# DS-001: TradingDecision Creation
# =============================================================================

class TestTradingDecisionCreation:
    """Test TradingDecision dataclass creation"""
    
    def test_full_creation(self):
        """DS-001: Create TradingDecision with all fields"""
        decision = TradingDecision(
            trade_id="test-uuid-12345678",
            timestamp=datetime(2026, 1, 1, 21, 0, 0),
            trigger_reason="scheduled",
            direction="hold",
            confidence=65,
            leverage=3,
            reasoning="All experts recommend HOLD.",
            entry_price=94500.50,
            tp_price=103950.55,
            sl_price=90720.48,
            amount_percent=0.2,
            leader_summary="Consensus: Cautious Hold.",
            agent_votes=[
                {"agent": "TechnicalAnalyst", "direction": "hold", "confidence": 70},
            ],
            position_context={"has_position": True, "direction": "long"},
            was_executed=True,
            execution_error=""
        )
        
        assert decision.trade_id == "test-uuid-12345678"
        assert decision.direction == "hold"
        assert decision.confidence == 65
        assert decision.leverage == 3
        assert decision.reasoning == "All experts recommend HOLD."
        assert decision.entry_price == 94500.50
        assert decision.tp_price == 103950.55
        assert decision.sl_price == 90720.48
        assert len(decision.agent_votes) == 1
        assert decision.was_executed == True
    
    def test_minimal_creation(self):
        """DS-001b: Create TradingDecision with minimal fields"""
        decision = TradingDecision(
            trade_id="minimal-test",
            timestamp=datetime.now()
        )
        
        # Check defaults
        assert decision.trade_id == "minimal-test"
        assert decision.direction == "hold"
        assert decision.confidence == 0
        assert decision.leverage == 1
        assert decision.reasoning == ""
        assert decision.agent_votes == []
        assert decision.position_context == {}
        assert decision.was_executed == False


# =============================================================================
# DS-002 to DS-003: Serialization and Deserialization
# =============================================================================

class TestTradingDecisionSerialization:
    """Test to_dict() and from_dict() methods"""
    
    def test_to_dict_serialization(self):
        """DS-002: to_dict() returns correct dict with ISO timestamp"""
        decision = TradingDecision(
            trade_id="test-serialize",
            timestamp=datetime(2026, 1, 1, 21, 0, 0),
            direction="hold",
            confidence=65,
            leverage=3,
            reasoning="Test reasoning",
            entry_price=94500.50,
            tp_price=103950.55,
            sl_price=90720.48
        )
        
        data = decision.to_dict()
        
        assert isinstance(data, dict)
        assert data['trade_id'] == "test-serialize"
        assert data['timestamp'] == "2026-01-01T21:00:00"
        assert data['direction'] == "hold"
        assert data['confidence'] == 65
        assert data['leverage'] == 3
    
    def test_from_dict_deserialization(self):
        """DS-003: from_dict() correctly restores object"""
        data = {
            'trade_id': 'test-deserialize',
            'timestamp': '2026-01-01T21:00:00',
            'trigger_reason': 'scheduled',
            'direction': 'hold',
            'confidence': 65,
            'leverage': 3,
            'reasoning': 'Test reasoning',
            'entry_price': 94500.50,
            'tp_price': 103950.55,
            'sl_price': 90720.48,
            'amount_percent': 0.2,
            'leader_summary': 'Test summary',
            'agent_votes': [{"agent": "TA", "direction": "hold"}],
            'position_context': {"has_position": False},
            'was_executed': True,
            'execution_error': ''
        }
        
        restored = TradingDecision.from_dict(data)
        
        assert restored.trade_id == 'test-deserialize'
        assert isinstance(restored.timestamp, datetime)
        assert restored.timestamp.year == 2026
        assert restored.direction == 'hold'
        assert len(restored.agent_votes) == 1


# =============================================================================
# DS-004 to DS-006: Edge Cases
# =============================================================================

class TestTradingDecisionEdgeCases:
    """Test edge cases for from_dict()"""
    
    def test_from_dict_missing_optional_fields(self):
        """DS-004: from_dict() handles missing optional fields"""
        data = {
            'trade_id': 'minimal',
            'timestamp': '2026-01-01T21:00:00',
        }
        
        restored = TradingDecision.from_dict(data)
        
        assert restored.trade_id == 'minimal'
        assert restored.direction == 'hold'  # default
        assert restored.confidence == 0  # default
        assert restored.leverage == 1  # default
        assert restored.agent_votes == []  # default
    
    def test_from_dict_extra_unknown_fields(self):
        """DS-005: from_dict() ignores unknown fields (forward compatibility)"""
        data = {
            'trade_id': 'extra-fields',
            'timestamp': '2026-01-01T21:00:00',
            'direction': 'hold',
            'confidence': 50,
            'unknown_future_field': 'some value',
            'another_new_field': 123
        }
        
        # Should not raise error
        restored = TradingDecision.from_dict(data)
        
        assert restored.trade_id == 'extra-fields'
        assert restored.direction == 'hold'
        assert not hasattr(restored, 'unknown_future_field')
    
    def test_from_dict_none_timestamp(self):
        """DS-006: from_dict() handles None timestamp"""
        data = {
            'trade_id': 'none-ts',
            'timestamp': None,
            'direction': 'hold'
        }
        
        restored = TradingDecision.from_dict(data)
        
        assert restored.trade_id == 'none-ts'
        assert isinstance(restored.timestamp, datetime)


# =============================================================================
# DS-007 to DS-008: Frontend Format
# =============================================================================

class TestTradingDecisionFrontendFormat:
    """Test to_frontend_format() method"""
    
    def test_to_frontend_format_structure(self):
        """DS-007: to_frontend_format() returns correct nested structure"""
        decision = TradingDecision(
            trade_id="frontend-test",
            timestamp=datetime(2026, 1, 1, 21, 0, 0),
            direction="hold",
            confidence=65,
            leverage=3,
            reasoning="Test reasoning",
            entry_price=94500.50,
            tp_price=103950.55,
            sl_price=90720.48,
            leader_summary="Consensus summary",
            agent_votes=[{"agent": "TA", "direction": "hold"}],
            was_executed=True
        )
        
        frontend = decision.to_frontend_format()
        
        # Top-level structure
        assert 'trade_id' in frontend
        assert 'timestamp' in frontend
        assert 'status' in frontend
        assert 'signal' in frontend
        assert 'agent_votes' in frontend
        assert 'position_context' in frontend
        
        # Status based on was_executed
        assert frontend['status'] == 'executed'
    
    def test_frontend_signal_dict_structure(self):
        """DS-008: Frontend signal dict has correct field names"""
        decision = TradingDecision(
            trade_id="signal-test",
            timestamp=datetime(2026, 1, 1, 21, 0, 0),
            direction="hold",
            confidence=65,
            leverage=3,
            reasoning="Test reasoning",
            entry_price=94500.50,
            tp_price=103950.55,
            sl_price=90720.48,
            leader_summary="Consensus summary"
        )
        
        frontend = decision.to_frontend_format()
        signal = frontend['signal']
        
        # Check signal dict fields
        assert signal['direction'] == 'hold'
        assert signal['confidence'] == 65
        assert signal['leverage'] == 3
        assert signal['reasoning'] == 'Test reasoning'
        assert signal['entry_price'] == 94500.50
        assert signal['take_profit_price'] == 103950.55  # NOT tp_price
        assert signal['stop_loss_price'] == 90720.48  # NOT sl_price
        assert signal['leader_summary'] == 'Consensus summary'


# =============================================================================
# DS-009 to DS-010: JSON Roundtrip
# =============================================================================

class TestTradingDecisionJsonRoundtrip:
    """Test JSON serialization roundtrip"""
    
    def test_json_roundtrip(self):
        """DS-009: Full JSON serialization roundtrip"""
        original = TradingDecision(
            trade_id="roundtrip-test",
            timestamp=datetime(2026, 1, 1, 21, 0, 0),
            direction="open_long",
            confidence=75,
            leverage=5,
            reasoning="Strong buy signal",
            entry_price=95000.0,
            tp_price=104500.0,
            sl_price=91200.0,
            leader_summary="Consensus: LONG",
            agent_votes=[{"agent": "TA", "direction": "long", "confidence": 80}],
            position_context={"has_position": False},
            was_executed=True
        )
        
        # Serialize to JSON
        json_str = json.dumps(original.to_dict(), ensure_ascii=False)
        
        # Deserialize back
        restored = TradingDecision.from_dict(json.loads(json_str))
        
        # Verify all fields match
        assert restored.trade_id == original.trade_id
        assert restored.direction == original.direction
        assert restored.confidence == original.confidence
        assert restored.leverage == original.leverage
        assert restored.tp_price == original.tp_price
        assert restored.sl_price == original.sl_price
        assert len(restored.agent_votes) == len(original.agent_votes)
    
    def test_agent_votes_serialization(self):
        """DS-010: agent_votes list serializes correctly"""
        votes = [
            {"agent": "TechnicalAnalyst", "direction": "long", "confidence": 75},
            {"agent": "SentimentAnalyst", "direction": "hold", "confidence": 60},
            {"agent": "MacroEconomist", "direction": "short", "confidence": 55},
        ]
        
        original = TradingDecision(
            trade_id="votes-test",
            timestamp=datetime.now(),
            agent_votes=votes
        )
        
        # Serialize and deserialize
        data = original.to_dict()
        restored = TradingDecision.from_dict(data)
        
        assert len(restored.agent_votes) == 3
        assert restored.agent_votes[0]['agent'] == 'TechnicalAnalyst'
        assert restored.agent_votes[1]['direction'] == 'hold'
        assert restored.agent_votes[2]['confidence'] == 55


# =============================================================================
# Store Tests (with mocked Redis)
# =============================================================================

class TestTradingDecisionStore:
    """Test TradingDecisionStore with mocked Redis"""
    
    @pytest.mark.asyncio
    async def test_save_decision(self):
        """Test saving a decision to Redis"""
        store = TradingDecisionStore()
        store._redis = FakeRedis()
        
        decision = TradingDecision(
            trade_id="save-test",
            timestamp=datetime.now(),
            direction="hold",
            confidence=65
        )
        
        result = await store.save_decision(decision)
        
        assert result == True
        assert "trading:decisions:save-test" in store._redis._data
    
    @pytest.mark.asyncio
    async def test_get_decision(self):
        """Test getting a decision from Redis"""
        store = TradingDecisionStore()
        store._redis = FakeRedis()
        
        # First save a decision
        decision = TradingDecision(
            trade_id="get-test",
            timestamp=datetime(2026, 1, 1, 21, 0, 0),
            direction="hold",
            confidence=65
        )
        await store.save_decision(decision)
        
        # Then retrieve it
        retrieved = await store.get_decision("get-test")
        
        assert retrieved is not None
        assert retrieved.trade_id == "get-test"
        assert retrieved.direction == "hold"
        assert retrieved.confidence == 65
    
    @pytest.mark.asyncio
    async def test_get_recent_decisions(self):
        """Test getting recent decisions"""
        store = TradingDecisionStore()
        store._redis = FakeRedis()
        
        # Save multiple decisions
        for i in range(5):
            decision = TradingDecision(
                trade_id=f"recent-{i}",
                timestamp=datetime.now(),
                direction="hold",
                confidence=50 + i * 5
            )
            await store.save_decision(decision)
        
        # Get recent decisions
        recent = await store.get_recent_decisions(limit=3)
        
        assert len(recent) == 3
        # Most recent first
        assert recent[0].trade_id == "recent-4"
    
    @pytest.mark.asyncio
    async def test_get_recent_decisions_for_frontend(self):
        """Test getting recent decisions formatted for frontend"""
        store = TradingDecisionStore()
        store._redis = FakeRedis()
        
        # Save a decision
        decision = TradingDecision(
            trade_id="frontend-recent",
            timestamp=datetime(2026, 1, 1, 21, 0, 0),
            direction="hold",
            confidence=65,
            tp_price=100000.0,
            sl_price=90000.0
        )
        await store.save_decision(decision)
        
        # Get for frontend
        frontend_list = await store.get_recent_decisions_for_frontend(limit=10)
        
        assert len(frontend_list) >= 1
        assert 'signal' in frontend_list[0]
        assert frontend_list[0]['signal']['take_profit_price'] == 100000.0


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
