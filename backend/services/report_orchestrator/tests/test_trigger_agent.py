import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.trading.trigger.agent import TriggerAgent, TriggerContext
from app.core.trading.trigger.fast_monitor import FastTriggerCondition, FastTriggerResult
from app.core.trading.trigger.lock import TriggerLock
from app.core.trading.trigger.news_crawler import NewsCrawler, NewsItem
from app.core.trading.trigger.scheduler import TriggerScheduler
from app.core.trading.trigger.scorer import TriggerScorer
from app.core.trading.trigger.ta_calculator import TACalculator, TAData


def test_news_crawler_impact_scoring():
    crawler = NewsCrawler()
    item = NewsItem(
        title="SEC approves Bitcoin ETF filing",
        source="TestSource",
        url="https://example.com/news",
    )

    crawler._calculate_impact(item)
    assert item.has_signal_keyword is True
    assert item.impact_score > 0


@pytest.mark.asyncio
async def test_ta_calculator_with_mocked_fetch(monkeypatch):
    calc = TACalculator(symbol="BTC-USDT-SWAP")

    async def _fake_fetch_all_candles(_session):
        return {
            "candles_15m": [],
            "candles_1h": [],
            "candles_4h": [],
            "ticker": {"last": "95000"},
        }

    monkeypatch.setattr(calc, "_fetch_all_candles", _fake_fetch_all_candles)

    data = await calc.calculate()
    assert isinstance(data, TAData)
    assert data.current_price == 95000.0


def test_trigger_scorer_low_high_scenarios():
    scorer = TriggerScorer(trigger_threshold=60)

    low_news = [NewsItem(title="Bitcoin daily update", source="Test", url="", has_signal_keyword=False)]
    low_ta = TAData(rsi_15m=50, price_change_15m=0.5, price_change_1h=1.0)
    low_score = scorer.calculate(low_news, low_ta)
    assert low_score.total < 60
    assert scorer.should_trigger(low_score) is False

    high_news = [
        NewsItem(title="SEC Approves Bitcoin ETF", source="CoinDesk", url="", has_signal_keyword=True),
        NewsItem(title="Fed signals rate cuts", source="Reuters", url="", has_signal_keyword=True),
    ]
    high_ta = TAData(
        rsi_15m=22,
        macd_crossover=True,
        volume_spike=True,
        price_change_15m=2.5,
        price_change_1h=4.0,
        trend_15m="bullish",
        trend_1h="bullish",
        trend_4h="bullish",
    )
    high_score = scorer.calculate(high_news, high_ta)
    assert high_score.total >= 60
    assert scorer.should_trigger(high_score) is True


@pytest.mark.asyncio
async def test_trigger_lock_lifecycle():
    lock = TriggerLock(cooldown_minutes=1)
    can, _ = lock.can_trigger()
    assert can is True

    acquired = await lock.acquire()
    assert acquired is True
    assert lock.state == "analyzing"

    lock.release(cooldown_minutes=1)
    assert lock.state == "cooldown"

    lock.force_release()
    assert lock.state == "idle"


@pytest.mark.asyncio
async def test_trigger_agent_check_with_mock_dependencies():
    fake_news_crawler = MagicMock()
    fake_news_crawler.fetch_latest = AsyncMock(return_value=[
        NewsItem(title="SEC Approves Bitcoin ETF", source="CoinDesk", url="", has_signal_keyword=True)
    ])

    fake_ta_calculator = MagicMock()
    fake_ta_calculator.calculate = AsyncMock(return_value=TAData(
        current_price=95000.0,
        price_change_15m=2.0,
        price_change_1h=3.5,
        rsi_15m=35.0,
    ))

    fake_llm = MagicMock()
    fake_llm.call = AsyncMock(return_value={
        "should_trigger": True,
        "urgency": "high",
        "confidence": 85,
        "reasoning": "Strong multi-factor signal",
        "key_events": ["ETF approval"],
    })

    agent = TriggerAgent(
        news_crawler=fake_news_crawler,
        ta_calculator=fake_ta_calculator,
        llm_helper=fake_llm,
        confidence_threshold=70,
    )

    should_trigger, context = await agent.check()
    assert should_trigger is True
    assert context.confidence == 85
    assert context.urgency == "high"
    assert context.current_price == 95000.0


@pytest.mark.asyncio
async def test_scheduler_runs_callback_when_triggered():
    fake_agent = MagicMock()
    trigger_context = TriggerContext(
        should_trigger=True,
        trigger_time="2026-01-01T00:00:00",
        confidence=88,
        urgency="high",
        reasoning="Test trigger",
    )
    fake_agent.check = AsyncMock(return_value=(True, trigger_context))
    fake_agent.get_status = MagicMock(return_value={"status": "ok"})

    fast_condition = FastTriggerCondition(
        name="PRICE_SPIKE_1M",
        value=2.1,
        threshold=1.5,
        direction="both",
        urgency="high",
        description="1m price spike",
    )
    fake_fast_monitor = MagicMock()
    fake_fast_monitor.check = AsyncMock(return_value=FastTriggerResult(
        should_trigger=True,
        conditions=[fast_condition],
        urgency="high",
        timestamp="2026-01-01T00:00:00",
    ))
    fake_fast_monitor.get_status = MagicMock(return_value={"status": "ok"})

    on_trigger = AsyncMock()
    scheduler = TriggerScheduler(
        trigger_agent=fake_agent,
        fast_monitor=fake_fast_monitor,
        trigger_lock=TriggerLock(cooldown_minutes=1),
        interval_minutes=15,
        on_trigger=on_trigger,
    )

    result = await scheduler.run_check()
    assert result["should_trigger"] is True
    assert result["callback_executed"] is True
    on_trigger.assert_awaited_once()
