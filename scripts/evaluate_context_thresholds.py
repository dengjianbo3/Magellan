#!/usr/bin/env python3
"""
Evaluate context/cache/routing metrics against threshold suggestions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def _safe_div(a: float, b: float) -> float:
    if b <= 0:
        return 0.0
    return a / b


def _load_summary_obj(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    if path.suffix.lower() == ".jsonl":
        decoder = json.JSONDecoder()
        idx = 0
        objects = []
        while idx < len(text):
            while idx < len(text) and text[idx].isspace():
                idx += 1
            if idx >= len(text):
                break
            obj, end = decoder.raw_decode(text, idx)
            objects.append(obj)
            idx = end
        if not objects:
            return {}
        last = objects[-1]
        return last.get("summary", {})
    return json.loads(text)


def _threshold_status(value: float, min_ok: float | None = None, max_ok: float | None = None) -> str:
    if min_ok is not None and value < min_ok:
        return "ALERT"
    if max_ok is not None and value > max_ok:
        return "ALERT"
    return "PASS"


def _metric_status_with_volume(
    value: float,
    volume: float,
    min_volume: float,
    min_ok: float | None = None,
    max_ok: float | None = None,
) -> str:
    if volume < min_volume:
        return "SKIP"
    return _threshold_status(value=value, min_ok=min_ok, max_ok=max_ok)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate magellan context metric thresholds")
    parser.add_argument("summary_file", help="summary JSON or summary.jsonl path")
    parser.add_argument(
        "--profile",
        choices=["auto", "steady", "warmup"],
        default="auto",
        help="Threshold profile: auto chooses warmup when route volume is low.",
    )
    parser.add_argument("--min-route-volume", type=float, default=20.0)
    parser.add_argument("--min-cache-volume", type=float, default=30.0)
    parser.add_argument("--min-tool-volume", type=float, default=30.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary = _load_summary_obj(Path(args.summary_file))
    cache_summary = summary.get("cache_summary", {})
    route_decisions = summary.get("route_decisions", {})
    tool_calls = summary.get("tool_calls", {})

    leader_hit = float((cache_summary.get("leader_route") or {}).get("hit_rate_pct", 0.0))
    technical_hit = float((cache_summary.get("technical_ohlcv") or {}).get("hit_rate_pct", 0.0))
    yahoo_hit = float((cache_summary.get("yahoo_finance") or {}).get("hit_rate_pct", 0.0))

    route_cached = float(route_decisions.get("leader:cached", 0.0) + route_decisions.get("delegated:cached", 0.0))
    route_total = sum(float(v) for v in route_decisions.values())
    route_cached_ratio_pct = _safe_div(route_cached, route_total) * 100.0

    route_error = sum(
        float(v)
        for k, v in route_decisions.items()
        if k.endswith(":error")
    )
    route_error_ratio_pct = _safe_div(route_error, route_total) * 100.0

    tool_success = sum(float(v) for k, v in tool_calls.items() if k.endswith(":success"))
    tool_error = sum(float(v) for k, v in tool_calls.items() if k.endswith(":error"))
    tool_total = tool_success + tool_error
    tool_error_ratio_pct = _safe_div(tool_error, tool_total) * 100.0

    leader_events = (cache_summary.get("leader_route") or {}).get("events", {})
    technical_events = (cache_summary.get("technical_ohlcv") or {}).get("events", {})
    yahoo_events = (cache_summary.get("yahoo_finance") or {}).get("events", {})

    leader_volume = float(leader_events.get("hit", 0.0) + leader_events.get("miss", 0.0) + leader_events.get("stale", 0.0))
    technical_volume = float(
        technical_events.get("hit", 0.0) + technical_events.get("miss", 0.0) + technical_events.get("stale", 0.0)
    )
    yahoo_volume = float(yahoo_events.get("hit", 0.0) + yahoo_events.get("miss", 0.0) + yahoo_events.get("stale", 0.0))

    thresholds = {
        "steady": {
            "leader_hit_min": 40.0,
            "technical_hit_min": 55.0,
            "yahoo_hit_min": 30.0,
            "route_cached_min": 20.0,
        },
        "warmup": {
            "leader_hit_min": 15.0,
            "technical_hit_min": 20.0,
            "yahoo_hit_min": 15.0,
            "route_cached_min": 10.0,
        },
    }
    active_profile = args.profile
    if active_profile == "auto":
        active_profile = "warmup" if route_total < args.min_route_volume else "steady"
    profile_threshold = thresholds[active_profile]

    checks = {
        "leader_route_hit_rate_pct": {
            "value": round(leader_hit, 2),
            "rule": f">= {profile_threshold['leader_hit_min']}",
            "volume": round(leader_volume, 2),
            "min_volume": args.min_cache_volume,
            "status": _metric_status_with_volume(
                value=leader_hit,
                volume=leader_volume,
                min_volume=args.min_cache_volume,
                min_ok=profile_threshold["leader_hit_min"],
            ),
        },
        "technical_ohlcv_hit_rate_pct": {
            "value": round(technical_hit, 2),
            "rule": f">= {profile_threshold['technical_hit_min']}",
            "volume": round(technical_volume, 2),
            "min_volume": args.min_cache_volume,
            "status": _metric_status_with_volume(
                value=technical_hit,
                volume=technical_volume,
                min_volume=args.min_cache_volume,
                min_ok=profile_threshold["technical_hit_min"],
            ),
        },
        "yahoo_finance_hit_rate_pct": {
            "value": round(yahoo_hit, 2),
            "rule": f">= {profile_threshold['yahoo_hit_min']}",
            "volume": round(yahoo_volume, 2),
            "min_volume": args.min_cache_volume,
            "status": _metric_status_with_volume(
                value=yahoo_hit,
                volume=yahoo_volume,
                min_volume=args.min_cache_volume,
                min_ok=profile_threshold["yahoo_hit_min"],
            ),
        },
        "route_cached_ratio_pct": {
            "value": round(route_cached_ratio_pct, 2),
            "rule": f">= {profile_threshold['route_cached_min']}",
            "volume": round(route_total, 2),
            "min_volume": args.min_route_volume,
            "status": _metric_status_with_volume(
                value=route_cached_ratio_pct,
                volume=route_total,
                min_volume=args.min_route_volume,
                min_ok=profile_threshold["route_cached_min"],
            ),
        },
        "route_error_ratio_pct": {
            "value": round(route_error_ratio_pct, 2),
            "rule": "<= 5",
            "volume": round(route_total, 2),
            "min_volume": args.min_route_volume,
            "status": _metric_status_with_volume(
                value=route_error_ratio_pct,
                volume=route_total,
                min_volume=args.min_route_volume,
                max_ok=5.0,
            ),
        },
        "tool_error_ratio_pct": {
            "value": round(tool_error_ratio_pct, 2),
            "rule": "<= 10",
            "volume": round(tool_total, 2),
            "min_volume": args.min_tool_volume,
            "status": _metric_status_with_volume(
                value=tool_error_ratio_pct,
                volume=tool_total,
                min_volume=args.min_tool_volume,
                max_ok=10.0,
            ),
        },
    }

    overall = "PASS"
    for item in checks.values():
        if item["status"] != "PASS":
            if item["status"] == "ALERT":
                overall = "ALERT"
                break
            overall = "PARTIAL"
    if overall == "ALERT":
        exit_code = 2
    else:
        exit_code = 0

    low_volume = {
        "leader_cache_volume": leader_volume,
        "technical_cache_volume": technical_volume,
        "yahoo_cache_volume": yahoo_volume,
        "route_volume": route_total,
        "tool_volume": tool_total,
    }

    skipped_checks = [name for name, item in checks.items() if item["status"] == "SKIP"]

    notes = []
    if skipped_checks:
        notes.append("Some checks were skipped due to low volume; expand sampling window or increase traffic.")
    if active_profile == "warmup":
        notes.append("Warmup profile active; switch to steady profile when route volume stabilizes.")
    if not notes:
        notes.append("All checks evaluated with sufficient data.")

    result = {
        "overall": overall,
        "profile": active_profile,
        "low_volume": low_volume,
        "skipped_checks": skipped_checks,
        "notes": notes,
        "checks": checks,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=== Context Threshold Evaluation ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
