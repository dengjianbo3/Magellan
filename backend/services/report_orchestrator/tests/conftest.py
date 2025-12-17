"""
PyTest Configuration and Fixtures

Shared fixtures for all tests.
"""

import pytest
import sys
import os

# Add app to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.mocks import (
    MockLLMGateway,
    MockTrader,
    VoteResponseGenerator
)


# ==================== LLM Fixtures ====================

@pytest.fixture
def mock_llm():
    """Provide mock LLM gateway."""
    gateway = MockLLMGateway()
    yield gateway
    gateway.reset()


@pytest.fixture
def mock_llm_with_long_vote(mock_llm):
    """Mock LLM that returns a long vote."""
    mock_llm.set_responses([VoteResponseGenerator.long_vote()])
    return mock_llm


@pytest.fixture
def mock_llm_with_short_vote(mock_llm):
    """Mock LLM that returns a short vote."""
    mock_llm.set_responses([VoteResponseGenerator.short_vote()])
    return mock_llm


@pytest.fixture
def mock_llm_with_hold_vote(mock_llm):
    """Mock LLM that returns a hold vote."""
    mock_llm.set_responses([VoteResponseGenerator.hold_vote()])
    return mock_llm


# ==================== Trader Fixtures ====================

@pytest.fixture
def mock_trader():
    """Provide mock trader."""
    trader = MockTrader(initial_balance=10000.0)
    yield trader
    trader.reset()


@pytest.fixture
def mock_trader_with_long_position(mock_trader):
    """Mock trader with an existing long position."""
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        mock_trader.open_long(leverage=3, amount_percent=0.2)
    )
    return mock_trader


@pytest.fixture
def mock_trader_with_short_position(mock_trader):
    """Mock trader with an existing short position."""
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        mock_trader.open_short(leverage=3, amount_percent=0.2)
    )
    return mock_trader


# ==================== Domain Fixtures ====================

@pytest.fixture
def sample_vote_json():
    """Sample vote JSON for testing."""
    return {
        "direction": "long",
        "confidence": 75,
        "leverage": 3,
        "take_profit_percent": 5.0,
        "stop_loss_percent": 2.0,
        "reasoning": "Test reasoning"
    }


@pytest.fixture
def sample_position_context():
    """Sample position context for testing."""
    from app.core.trading.domain.position import PositionContext
    
    return PositionContext(
        has_position=True,
        direction="long",
        size=0.1,
        entry_price=50000.0,
        current_price=51000.0,
        leverage=3,
        unrealized_pnl=100.0,
        unrealized_pnl_percent=6.0
    )


@pytest.fixture
def empty_position_context():
    """Empty position context (no position)."""
    from app.core.trading.domain.position import PositionContext
    
    return PositionContext(has_position=False)


# ==================== Meeting Fixtures ====================

@pytest.fixture
def meeting_config():
    """Default meeting configuration."""
    from app.core.trading.meeting.config import MeetingConfig
    
    return MeetingConfig(
        symbol="BTC-USDT-SWAP",
        max_leverage=10,
        default_leverage=3,
        phase_timeout=30,  # Short timeout for tests
        agent_timeout=10
    )


# ==================== Async Support ====================

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
