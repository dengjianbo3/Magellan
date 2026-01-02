#!/usr/bin/env python3
"""
TriggerAgent 独立测试脚本

测试触发器系统的所有组件，不依赖主系统。
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# 添加触发器模块路径 (直接导入，避免 redis 依赖)
trigger_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    '..', 'app', 'core', 'trading', 'trigger'
)
sys.path.insert(0, trigger_path)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def success(self, msg: str = ""):
        self.passed += 1
        print(f"  ✅ {msg}")
    
    def fail(self, msg: str, error: str = ""):
        self.failed += 1
        self.errors.append(f"{msg}: {error}")
        print(f"  ❌ {msg}: {error}")


async def test_news_crawler():
    """测试新闻爬虫"""
    print("\n" + "="*60)
    print("📰 Testing NewsCrawler")
    print("="*60)
    
    result = TestResult("NewsCrawler")
    
    try:
        from news_crawler import NewsCrawler, SIGNAL_KEYWORDS, NOISE_KEYWORDS
        
        # 测试实例化
        crawler = NewsCrawler(timeout=15, max_age_minutes=60)
        result.success("Instantiation")
        
        # 测试关键词定义
        if len(SIGNAL_KEYWORDS) > 0:
            result.success(f"Signal keywords defined ({len(SIGNAL_KEYWORDS)} keywords)")
        else:
            result.fail("Signal keywords", "Empty list")
        
        if len(NOISE_KEYWORDS) > 0:
            result.success(f"Noise keywords defined ({len(NOISE_KEYWORDS)} keywords)")
        else:
            result.fail("Noise keywords", "Empty list")
        
        # 测试爬取
        print("\n  Fetching news (this may take a few seconds)...")
        news_items = await crawler.fetch_latest()
        
        if news_items:
            result.success(f"Fetched {len(news_items)} news items")
            
            # 显示样本
            print("\n  Sample news:")
            for item in news_items[:3]:
                print(f"    [{item.source}] {item.title[:60]}...")
                print(f"      Signal: {item.has_signal_keyword}, Impact: {item.impact_score}")
        else:
            result.fail("Fetch news", "No items returned (network issue?)")
        
    except Exception as e:
        result.fail("NewsCrawler test", str(e))
    
    return result


async def test_ta_calculator():
    """测试技术分析计算器"""
    print("\n" + "="*60)
    print("📊 Testing TACalculator")
    print("="*60)
    
    result = TestResult("TACalculator")
    
    try:
        from ta_calculator import TACalculator
        
        # 测试实例化
        calc = TACalculator(symbol="BTC-USDT-SWAP")
        result.success("Instantiation")
        
        # 测试计算
        print("\n  Calculating indicators (fetching from OKX)...")
        data = await calc.calculate()
        
        # 验证数据
        if data.current_price > 0:
            result.success(f"Current price: ${data.current_price:,.2f}")
        else:
            result.fail("Current price", "Zero or invalid")
        
        if 0 <= data.rsi_15m <= 100:
            result.success(f"RSI (15m): {data.rsi_15m}")
        else:
            result.fail("RSI calculation", f"Invalid value: {data.rsi_15m}")
        
        result.success(f"MACD crossover: {data.macd_crossover}")
        result.success(f"Volume spike: {data.volume_spike}")
        result.success(f"Price change (15m): {data.price_change_15m}%")
        result.success(f"Trend (15m/1h/4h): {data.trend_15m}/{data.trend_1h}/{data.trend_4h}")
        
    except Exception as e:
        result.fail("TACalculator test", str(e))
    
    return result


async def test_scorer():
    """测试评分器"""
    print("\n" + "="*60)
    print("🎯 Testing TriggerScorer")
    print("="*60)
    
    result = TestResult("TriggerScorer")
    
    try:
        from scorer import TriggerScorer
        from news_crawler import NewsItem
        from ta_calculator import TAData
        
        scorer = TriggerScorer(trigger_threshold=60)
        result.success("Instantiation")
        
        # 测试场景 1: 低分 (不触发)
        news_low = [
            NewsItem(title="Bitcoin price analysis today", source="Test", url="", has_signal_keyword=False)
        ]
        ta_low = TAData(rsi_15m=50, price_change_15m=0.5, price_change_1h=1.0)
        
        score_low = scorer.calculate(news_low, ta_low)
        if score_low.total < 60:
            result.success(f"Low score scenario: {score_low.total} (should NOT trigger)")
        else:
            result.fail("Low score scenario", f"Expected <60, got {score_low.total}")
        
        # 测试场景 2: 高分 (触发)
        news_high = [
            NewsItem(title="SEC Approves Bitcoin ETF", source="CoinDesk", url="", has_signal_keyword=True),
            NewsItem(title="Fed announces rate cut", source="Reuters", url="", has_signal_keyword=True)
        ]
        ta_high = TAData(
            rsi_15m=22,  # 极值
            macd_crossover=True,
            volume_spike=True,
            price_change_15m=2.5,  # 高波动
            price_change_1h=4.0
        )
        
        score_high = scorer.calculate(news_high, ta_high)
        if score_high.total >= 60:
            result.success(f"High score scenario: {score_high.total} (SHOULD trigger)")
        else:
            result.fail("High score scenario", f"Expected >=60, got {score_high.total}")
        
        # 详细分数
        print(f"\n  Score breakdown (high scenario):")
        print(f"    News score: {score_high.news_score}")
        print(f"    Price score: {score_high.price_score}")
        print(f"    TA score: {score_high.ta_score}")
        
    except Exception as e:
        result.fail("TriggerScorer test", str(e))
    
    return result


async def test_lock():
    """测试锁机制"""
    print("\n" + "="*60)
    print("🔒 Testing TriggerLock")
    print("="*60)
    
    result = TestResult("TriggerLock")
    
    try:
        from lock import TriggerLock
        
        lock = TriggerLock(cooldown_minutes=1)
        result.success("Instantiation")
        
        # 初始状态
        can, reason = lock.can_trigger()
        if can and lock.state == "idle":
            result.success("Initial state: idle, can trigger")
        else:
            result.fail("Initial state", f"state={lock.state}, can={can}")
        
        # 获取锁
        acquired = await lock.acquire()
        if acquired and lock.state == "analyzing":
            result.success("Lock acquired, state: analyzing")
        else:
            result.fail("Lock acquire", f"acquired={acquired}, state={lock.state}")
        
        # 获取锁时不能再触发
        can, reason = lock.can_trigger()
        if not can:
            result.success(f"Cannot trigger while analyzing: {reason}")
        else:
            result.fail("Lock blocking", "Should not be able to trigger")
        
        # 释放锁
        lock.release(cooldown_minutes=1)
        if lock.state == "cooldown":
            result.success("Lock released, state: cooldown")
        else:
            result.fail("Lock release", f"state={lock.state}")
        
        # 强制释放
        lock.force_release()
        if lock.state == "idle":
            result.success("Force released, state: idle")
        else:
            result.fail("Force release", f"state={lock.state}")
        
    except Exception as e:
        result.fail("TriggerLock test", str(e))
    
    return result


async def test_trigger_agent():
    """测试 TriggerAgent 主类"""
    print("\n" + "="*60)
    print("🚀 Testing TriggerAgent (Full Integration)")
    print("="*60)
    
    result = TestResult("TriggerAgent")
    
    try:
        from agent import TriggerAgent
        
        agent = TriggerAgent()
        result.success("Instantiation")
        
        # 执行检查
        print("\n  Running full check (news + TA)...")
        start = datetime.now()
        
        should_trigger, context = await agent.check()
        
        elapsed = (datetime.now() - start).total_seconds()
        
        # 验证执行时间
        if elapsed < 15:  # 应该在 15 秒内完成
            result.success(f"Check completed in {elapsed:.2f}s")
        else:
            result.fail("Execution time", f"{elapsed:.2f}s (too slow)")
        
        # 验证返回
        result.success(f"Score: {context.score}")
        result.success(f"Should trigger: {should_trigger}")
        result.success(f"Current price: ${context.current_price:,.2f}")
        
        # 显示详情
        print(f"\n  Details:")
        print(f"    Price change (15m): {context.price_change_15m}%")
        print(f"    Price change (1h): {context.price_change_1h}%")
        print(f"    RSI (15m): {context.rsi_15m}")
        if context.news_summary:
            print(f"    Signal news: {len(context.news_summary)} items")
            for title in context.news_summary[:2]:
                print(f"      - {title[:50]}...")
        
    except Exception as e:
        result.fail("TriggerAgent test", str(e))
    
    return result


async def test_scheduler():
    """测试调度器"""
    print("\n" + "="*60)
    print("⏰ Testing TriggerScheduler")
    print("="*60)
    
    result = TestResult("TriggerScheduler")
    
    try:
        from scheduler import TriggerScheduler
        from agent import TriggerContext
        
        trigger_called = False
        trigger_context = None
        
        async def mock_callback(ctx: TriggerContext):
            nonlocal trigger_called, trigger_context
            trigger_called = True
            trigger_context = ctx
            print(f"  [CALLBACK] Would trigger main analysis with score={ctx.score}")
        
        scheduler = TriggerScheduler(
            interval_minutes=15,
            on_trigger=mock_callback
        )
        result.success("Instantiation")
        
        # 单次检查
        print("\n  Running single check...")
        check_result = await scheduler.run_check()
        
        result.success(f"Check #{check_result['check_number']} completed")
        
        if check_result.get('skipped'):
            result.success(f"Skipped: {check_result.get('reason')}")
        else:
            result.success(f"Score: {check_result.get('score', 0)}")
            result.success(f"Should trigger: {check_result.get('should_trigger', False)}")
        
        # 状态
        status = scheduler.get_status()
        result.success(f"Scheduler state: {status['state']}")
        result.success(f"Lock state: {status['lock']['state']}")
        
    except Exception as e:
        result.fail("TriggerScheduler test", str(e))
    
    return result


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧪 TriggerAgent System Tests")
    print("="*60)
    print(f"Time: {datetime.now().isoformat()}")
    
    results = []
    
    # 运行测试
    results.append(await test_news_crawler())
    results.append(await test_ta_calculator())
    results.append(await test_scorer())
    results.append(await test_lock())
    results.append(await test_trigger_agent())
    results.append(await test_scheduler())
    
    # 汇总
    print("\n" + "="*60)
    print("📋 Test Summary")
    print("="*60)
    
    total_passed = 0
    total_failed = 0
    
    for r in results:
        status = "✅" if r.failed == 0 else "❌"
        print(f"  {status} {r.name}: {r.passed} passed, {r.failed} failed")
        total_passed += r.passed
        total_failed += r.failed
        
        for err in r.errors:
            print(f"      └── {err}")
    
    print("\n" + "-"*60)
    print(f"  Total: {total_passed} passed, {total_failed} failed")
    
    if total_failed == 0:
        print("\n  🎉 All tests passed!")
    else:
        print(f"\n  ⚠️ {total_failed} tests failed")
    
    print("="*60 + "\n")
    
    return total_failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
