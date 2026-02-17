import pytest

from app.core.trading.agent_memory import AgentMemoryStore, PredictionStore, get_reflection_generator
from app.core.trading.decision_store import TradingDecisionStore
from app.core.trading.market_data_snapshot import get_market_snapshot_manager, reset_market_snapshot_manager
from app.core.trading.mode_manager import get_mode_manager
from app.core.trading.okx_credentials_store import OkxCredentialsStore
from app.core.trading.okx_trader import OKXTrader
from app.core.trading.paper_trader import PaperTrader
from app.core.trading.trading_logger import TradingLogger
from app.core.trading.trading_settings_store import TradingSettingsStore
from app.core.trading.weight_learner import AgentWeightLearner
from app.services import trading_system as ts


def test_storage_keys_are_user_scoped():
    settings = TradingSettingsStore()
    assert settings._key("u1").endswith(":u1")
    assert settings._key("u2").endswith(":u2")

    creds = OkxCredentialsStore()
    assert creds._key("u1").endswith(":u1")
    assert creds._key("u2").endswith(":u2")

    decisions = TradingDecisionStore(user_id="u1")
    assert decisions.key_prefix.endswith("u1:")
    assert decisions.recent_list_key.endswith(":u1")

    mem = AgentMemoryStore(user_id="u1")
    pred = PredictionStore(user_id="u1")
    assert mem.key_prefix.endswith(":u1:")
    assert pred.key_prefix.endswith(":u1:")

    logger = TradingLogger(user_id="u1")
    assert logger.decisions_key.endswith(":u1")
    assert logger.positions_key.endswith(":u1")

    weights = AgentWeightLearner(user_id="u1")
    assert weights.redis_key_prefix.endswith(":u1:")
    assert weights.redis_key_performance.endswith(":u1:")


def test_trader_state_prefixes_are_user_scoped():
    paper_u1 = PaperTrader(user_id="u1")
    paper_u2 = PaperTrader(user_id="u2")
    assert paper_u1._key_prefix.endswith(":u1:")
    assert paper_u2._key_prefix.endswith(":u2:")
    assert paper_u1._key_prefix != paper_u2._key_prefix

    okx_u1 = OKXTrader(user_id="u1")
    okx_u2 = OKXTrader(user_id="u2")
    assert okx_u1._key_prefix.endswith(":u1:")
    assert okx_u2._key_prefix.endswith(":u2:")
    assert okx_u1._key_prefix != okx_u2._key_prefix


def test_mode_manager_is_user_scoped():
    m1 = get_mode_manager("u1")
    m2 = get_mode_manager("u2")
    m1_again = get_mode_manager("u1")
    assert m1 is m1_again
    assert m1 is not m2
    assert m1.redis_key_mode.endswith(":u1")
    assert m2.redis_key_mode.endswith(":u2")


def test_market_snapshot_manager_is_user_scoped():
    reset_market_snapshot_manager()
    s1 = get_market_snapshot_manager("u1")
    s2 = get_market_snapshot_manager("u2")
    s1_again = get_market_snapshot_manager("u1")
    assert s1 is s1_again
    assert s1 is not s2
    assert s1.user_id == "u1"
    assert s2.user_id == "u2"


def test_reflection_generator_is_user_scoped():
    g1 = get_reflection_generator("u1")
    g2 = get_reflection_generator("u2")
    g1_again = get_reflection_generator("u1")
    assert g1 is g1_again
    assert g1 is not g2


@pytest.mark.asyncio
async def test_trading_system_singleton_is_scoped_by_user(monkeypatch):
    async def _fake_initialize(self):
        self._initialized = True

    monkeypatch.setattr(ts.TradingSystem, "initialize", _fake_initialize)
    ts._trading_systems.clear()

    s1 = await ts.get_trading_system(user_id="u1")
    s2 = await ts.get_trading_system(user_id="u2")
    s1_again = await ts.get_trading_system(user_id="u1")

    assert s1 is s1_again
    assert s1 is not s2
    assert s1.user_id == "u1"
    assert s2.user_id == "u2"
