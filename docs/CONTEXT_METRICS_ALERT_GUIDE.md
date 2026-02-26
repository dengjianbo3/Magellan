# Context Metrics Alert Guide

## Scope
- `magellan_context_cache_events_total`
- `magellan_context_route_decisions_total`
- `magellan_context_tool_calls_total`

## Suggested Thresholds

### Steady State (recommended target)
- `leader_route` cache hit rate: `>= 40%`
- `technical_ohlcv` cache hit rate: `>= 55%`
- `yahoo_finance` cache hit rate: `>= 30%`
- route cached ratio (`status="cached"` / total route decisions): `>= 20%`
- route error ratio (`status="error"` / total route decisions): `<= 5%`
- tool error ratio (`status="error"` / (success+error)): `<= 10%`

### Warm-up / Low-traffic Window (temporary threshold)
- `leader_route` cache hit rate: `>= 15%`
- `technical_ohlcv` cache hit rate: `>= 20%`
- `yahoo_finance` cache hit rate: `>= 15%`
- route cached ratio (`status="cached"` / total route decisions): `>= 10%`
- route error ratio (`status="error"` / total route decisions): `<= 5%`
- tool error ratio (`status="error"` / (success+error)): `<= 10%`

### Minimum Volume Gate (must satisfy before alert)
- route decisions (window): `>= 20`
- cache decision denominator (`hit+miss+stale` per layer): `>= 30`
- tool calls (`success+error`): `>= 30`

## Live Sampling Snapshot (2026-02-26)
- File: `tmp/phase0_baseline_window_live_route_probe/summary.jsonl`
- `leader_route` hit rate: `20.0%`
- `technical_ohlcv` hit rate: `25.0%`
- `yahoo_finance` hit rate: `20.0%`
- route cached ratio: `20.0%`
- route error ratio: `0.0%`
- tool error ratio: `0.0%`

## PromQL Examples

### 1) Leader Route Cache Hit Rate (5m)
```promql
100 *
sum(rate(magellan_context_cache_events_total{layer="leader_route",event="hit"}[5m]))
/
sum(rate(magellan_context_cache_events_total{layer="leader_route",event=~"hit|miss|stale"}[5m]))
```

### 2) Technical OHLCV Cache Hit Rate (5m)
```promql
100 *
sum(rate(magellan_context_cache_events_total{layer="technical_ohlcv",event="hit"}[5m]))
/
sum(rate(magellan_context_cache_events_total{layer="technical_ohlcv",event=~"hit|miss|stale"}[5m]))
```

### 3) Route Error Ratio (5m)
```promql
100 *
sum(rate(magellan_context_route_decisions_total{status="error"}[5m]))
/
sum(rate(magellan_context_route_decisions_total[5m]))
```

### 4) Tool Error Ratio (5m)
```promql
100 *
sum(rate(magellan_context_tool_calls_total{status="error"}[5m]))
/
sum(rate(magellan_context_tool_calls_total{status=~"success|error"}[5m]))
```

## Alert Rules (Example)
- `warning`: route error ratio > `3%` for `10m`
- `critical`: route error ratio > `5%` for `10m`
- `warning`: tool error ratio > `8%` for `15m`
- `critical`: tool error ratio > `10%` for `15m`
- `warning`: leader route cache hit rate < `30%` for `15m` (steady state)
- `critical`: leader route cache hit rate < `20%` for `15m` (steady state)
- `warning`: leader route cache hit rate < `15%` for `15m` (warm-up only)
- `critical`: leader route cache hit rate < `10%` for `15m` (warm-up only)

## Prometheus Rule File
- 已提供可落地规则模板: `ops/prometheus/context_metrics_alert_rules.yml`
- 建议在 Prometheus 配置中加入:
  - `rule_files:`
  - `  - /etc/prometheus/rules/context_metrics_alert_rules.yml`
- 并将该文件映射到容器路径 `/etc/prometheus/rules/context_metrics_alert_rules.yml`

## Operational Notes
- Cache hit rates should be judged by **window rate**, not absolute counters.
- For low traffic periods, avoid noisy alerts by setting `for` windows and minimum request volume gates.
- If `/metrics` scraping is slow under load, increase scrape timeout and reduce label cardinality.
- Sampling recommendation:
  - `DURATION_MINUTES=30 INTERVAL_SECONDS=30 ./scripts/run_context_baseline_window_in_container.sh`
  - `python3 scripts/evaluate_context_thresholds.py <summary.jsonl> --json --profile auto --min-route-volume 20 --min-cache-volume 30 --min-tool-volume 30`
