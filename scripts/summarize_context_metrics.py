#!/usr/bin/env python3
"""
Summarize magellan_context_* Prometheus metrics from a metrics slice file.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from typing import Dict, Tuple


LINE_RE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+(-?\d+(?:\.\d+)?)$")
LABEL_RE = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="([^"]*)"')


def parse_labels(raw: str) -> Dict[str, str]:
    if not raw:
        return {}
    body = raw.strip()[1:-1]  # trim {}
    labels = {}
    for k, v in LABEL_RE.findall(body):
        labels[k] = v
    return labels


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize magellan_context_* metrics")
    parser.add_argument("file", help="Path to .prom metrics file")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    counters: Dict[str, float] = defaultdict(float)
    cache_by_layer: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    route_by_mode_status: Dict[Tuple[str, str], float] = defaultdict(float)
    tool_by_channel_status: Dict[Tuple[str, str], float] = defaultdict(float)

    with open(args.file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = LINE_RE.match(line)
            if not m:
                continue
            metric, raw_labels, val_raw = m.groups()
            if not metric.startswith("magellan_context_"):
                continue
            val = float(val_raw)
            labels = parse_labels(raw_labels or "")

            counters[metric] += val

            if metric == "magellan_context_cache_events_total":
                layer = labels.get("layer", "unknown")
                event = labels.get("event", "unknown")
                cache_by_layer[layer][event] += val
            elif metric == "magellan_context_route_decisions_total":
                mode = labels.get("mode", "unknown")
                status = labels.get("status", "unknown")
                route_by_mode_status[(mode, status)] += val
            elif metric == "magellan_context_tool_calls_total":
                channel = labels.get("channel", "unknown")
                status = labels.get("status", "unknown")
                tool_by_channel_status[(channel, status)] += val

    cache_summary = {}
    for layer, events in cache_by_layer.items():
        hits = events.get("hit", 0.0)
        misses = events.get("miss", 0.0)
        stales = events.get("stale", 0.0)
        denominator = hits + misses + stales
        hit_rate = (hits / denominator * 100.0) if denominator > 0 else 0.0
        cache_summary[layer] = {
            "events": dict(events),
            "hit_rate_pct": round(hit_rate, 2),
        }

    output = {
        "totals": dict(counters),
        "cache_summary": cache_summary,
        "route_decisions": {
            f"{mode}:{status}": count
            for (mode, status), count in sorted(route_by_mode_status.items())
        },
        "tool_calls": {
            f"{channel}:{status}": count
            for (channel, status), count in sorted(tool_by_channel_status.items())
        },
    }

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("=== Context Metrics Summary ===")
        print(json.dumps(output, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

