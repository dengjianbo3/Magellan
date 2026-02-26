#!/usr/bin/env python3
"""
Phase benchmark for Skills + Cache + Routing optimization.

This benchmark runs inside report_orchestrator runtime and validates:
1) Leader route cache effectiveness
2) Technical OHLCV cache effectiveness
3) Yahoo Finance action cache effectiveness
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import pandas as pd
from prometheus_client import generate_latest


def _pct_improvement(cold: float, warm: float) -> float:
    if cold <= 0:
        return 0.0
    return max(0.0, (cold - warm) / cold * 100.0)


def _metrics_slice(prefixes: list[str]) -> Dict[str, float]:
    blob = generate_latest().decode("utf-8")
    out: Dict[str, float] = {}
    for line in blob.splitlines():
        if line.startswith("#"):
            continue
        for p in prefixes:
            if line.startswith(p):
                key, _, val = line.partition(" ")
                try:
                    out[key] = float(val)
                except Exception:
                    pass
                break
    return out


async def benchmark_leader_route(simulated_latency: float) -> Dict[str, Any]:
    import app.main as orchestrator_main

    orchestrator_main._leader_route_cache.clear()
    original_llm = orchestrator_main._llm_chat_completion
    calls = {"llm": 0}

    async def fake_llm(messages, temperature=1.0, provider=None, attachments=None, model=None):
        calls["llm"] += 1
        await asyncio.sleep(simulated_latency)
        return (
            '{"need_specialists": false, "specialists": [], '
            '"leader_reply": "cache benchmark", "reason": "benchmark"}'
        )

    orchestrator_main._llm_chat_completion = fake_llm
    try:
        args = dict(
            user_message="请分析BTC短期走势",
            history=[{"role": "user", "content": "BTC短期走势"}],
            language="zh",
            knowledge_enabled=True,
            knowledge_category="all",
            attachments_summary="none",
        )

        t0 = time.perf_counter()
        first = await orchestrator_main._leader_plan_route(**args)
        cold = time.perf_counter() - t0

        t1 = time.perf_counter()
        second = await orchestrator_main._leader_plan_route(**args)
        warm = time.perf_counter() - t1
    finally:
        orchestrator_main._llm_chat_completion = original_llm

    return {
        "cold_seconds": round(cold, 4),
        "warm_seconds": round(warm, 4),
        "improvement_pct": round(_pct_improvement(cold, warm), 2),
        "llm_calls": calls["llm"],
        "cache_entries": len(orchestrator_main._leader_route_cache),
        "decision_equal": first == second,
    }


async def benchmark_technical_cache(simulated_latency: float) -> Dict[str, Any]:
    from app.core.roundtable.technical_tools import TechnicalAnalysisTools

    tool = TechnicalAnalysisTools()
    tool._ohlcv_cache.clear()
    calls = {"source": 0}
    original_fetch = tool._get_crypto_ohlcv

    async def fake_fetch(symbol: str, timeframe: str, limit: int):
        calls["source"] += 1
        await asyncio.sleep(simulated_latency)
        now = datetime.utcnow()
        rows = []
        for i in range(limit):
            base = float(i + 1)
            rows.append(
                {
                    "timestamp": now - timedelta(minutes=limit - i),
                    "open": base,
                    "high": base + 0.5,
                    "low": base - 0.5,
                    "close": base + 0.1,
                    "volume": 100 + i,
                }
            )
        return pd.DataFrame(rows)

    tool._get_crypto_ohlcv = fake_fetch
    try:
        t0 = time.perf_counter()
        _ = await tool.get_ohlcv("BTC/USDT", "1h", 120, "crypto")
        cold = time.perf_counter() - t0

        t1 = time.perf_counter()
        _ = await tool.get_ohlcv("BTC/USDT", "1h", 120, "crypto")
        warm = time.perf_counter() - t1
    finally:
        tool._get_crypto_ohlcv = original_fetch

    return {
        "cold_seconds": round(cold, 4),
        "warm_seconds": round(warm, 4),
        "improvement_pct": round(_pct_improvement(cold, warm), 2),
        "source_calls": calls["source"],
        "cache_entries": len(tool._ohlcv_cache),
    }


async def benchmark_yahoo_cache(simulated_latency: float) -> Dict[str, Any]:
    from app.core.roundtable.yahoo_finance_tool import YahooFinanceTool

    tool = YahooFinanceTool()
    tool._cache_store.clear()
    calls = {"price": 0, "news": 0}
    original_price = tool._get_current_price
    original_news = tool._get_news

    async def fake_price(ticker, symbol: str):
        calls["price"] += 1
        await asyncio.sleep(simulated_latency)
        return {
            "success": True,
            "summary": f"{symbol} mock price",
            "data": {"symbol": symbol, "price": 123.45},
        }

    async def fake_news(ticker, symbol: str):
        calls["news"] += 1
        await asyncio.sleep(simulated_latency)
        return {
            "success": False,
            "summary": f"{symbol} mock news failed",
        }

    tool._get_current_price = fake_price
    tool._get_news = fake_news
    try:
        t0 = time.perf_counter()
        _ = await tool.execute(action="price", symbol="AAPL")
        cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        _ = await tool.execute(action="price", symbol="AAPL")
        warm = time.perf_counter() - t1

        # Failed results should NOT be cached.
        _ = await tool.execute(action="news", symbol="AAPL")
        _ = await tool.execute(action="news", symbol="AAPL")
    finally:
        tool._get_current_price = original_price
        tool._get_news = original_news

    return {
        "cold_seconds": round(cold, 4),
        "warm_seconds": round(warm, 4),
        "improvement_pct": round(_pct_improvement(cold, warm), 2),
        "price_source_calls": calls["price"],
        "news_source_calls": calls["news"],
        "cache_entries": len(tool._cache_store),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run cache/routing benchmark for report_orchestrator")
    parser.add_argument("--latency", type=float, default=0.2, help="Simulated upstream latency in seconds")
    parser.add_argument("--json", action="store_true", help="Print pure JSON output")
    args = parser.parse_args()

    before_metrics = _metrics_slice(
        [
            "magellan_context_cache_events_total",
            "magellan_context_route_decisions_total",
        ]
    )

    leader = await benchmark_leader_route(simulated_latency=args.latency)
    technical = await benchmark_technical_cache(simulated_latency=args.latency)
    yahoo = await benchmark_yahoo_cache(simulated_latency=args.latency)

    after_metrics = _metrics_slice(
        [
            "magellan_context_cache_events_total",
            "magellan_context_route_decisions_total",
        ]
    )

    result = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "simulated_latency_seconds": args.latency,
        "leader_route_cache": leader,
        "technical_ohlcv_cache": technical,
        "yahoo_action_cache": yahoo,
        "metrics_before": before_metrics,
        "metrics_after": after_metrics,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=== Skills+Cache+Routing Benchmark ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    # Basic success gate.
    passed = (
        leader["llm_calls"] == 1
        and leader["decision_equal"]
        and technical["source_calls"] == 1
        and yahoo["price_source_calls"] == 1
        and yahoo["news_source_calls"] == 2
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

