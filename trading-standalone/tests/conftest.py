import sys
import os
import pytest
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend" / "services" / "report_orchestrator"))

# Configure asyncio for pytest
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Import fixtures
from tests.fixtures.market_data import *
from tests.fixtures.agent_responses import *
from tests.fixtures.price_scenarios import *

# Import mocks
from tests.mocks.mock_llm import *
from tests.mocks.mock_price_service import *
from tests.mocks.mock_web_search import *


@pytest.fixture
def mock_redis(mocker):
    """Mock Redis for testing without real Redis"""
    import fakeredis.aioredis
    redis_mock = fakeredis.aioredis.FakeRedis()
    mocker.patch("redis.from_url", return_value=redis_mock)
    return redis_mock


@pytest.fixture
async def clean_paper_trader():
    """Provide a clean PaperTrader instance for each test"""
    from app.core.trading.paper_trader import PaperTrader, PaperTraderConfig
    
    config = PaperTraderConfig(
        initial_balance=10000.0,
        redis_url="redis://localhost:6379",
        demo_mode=True,  # Use demo mode for testing
        max_leverage=10,
        default_tp_percent=5.0,
        default_sl_percent=2.0
    )
    
    trader = PaperTrader(config=config)
    await trader.initialize()
    
    yield trader
    
    # Cleanup
    if trader._redis:
        await trader._redis.flushdb()


@pytest.fixture
def mock_config():
    """Provide a mock TradingMeetingConfig"""
    from app.core.trading.trading_meeting import TradingMeetingConfig
    
    return TradingMeetingConfig(
        symbol="BTC-USDT-SWAP",
        max_leverage=10,
        min_position_percent=0.05,
        max_position_percent=0.3,
        default_position_percent=0.2,
        min_confidence=60,
        default_tp_percent=5.0,
        default_sl_percent=2.0,
        default_balance=10000.0,
        fallback_price=95000.0
    )


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "critical: Critical functionality tests")
    config.addinivalue_line("markers", "asyncio: Async tests")


def pytest_collection_modifyitems(config, items):
    """Auto-mark async tests"""
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
