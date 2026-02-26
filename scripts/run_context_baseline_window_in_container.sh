#!/usr/bin/env bash
set -euo pipefail

SERVICE="${SERVICE:-report_orchestrator}"
DURATION_MINUTES="${DURATION_MINUTES:-10}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-60}"
OUT_DIR="${OUT_DIR:-./tmp/phase0_baseline_window_live}"
REQUEST_TIMEOUT_SECONDS="${REQUEST_TIMEOUT_SECONDS:-120}"
MAX_RETRIES="${MAX_RETRIES:-3}"
RETRY_DELAY_SECONDS="${RETRY_DELAY_SECONDS:-3}"

mkdir -p "${OUT_DIR}"
SUMMARY_JSONL="${OUT_DIR}/summary.jsonl"
: > "${SUMMARY_JSONL}"

end_epoch=$(( $(date +%s) + DURATION_MINUTES * 60 ))
iteration=0

echo "[live-window] service=${SERVICE} duration=${DURATION_MINUTES}m interval=${INTERVAL_SECONDS}s"
echo "[live-window] output=${OUT_DIR}"

while [ "$(date +%s)" -lt "${end_epoch}" ]; do
  iteration=$((iteration + 1))
  ts="$(date -u +"%Y%m%d_%H%M%S")"
  raw_file="${OUT_DIR}/metrics_${ts}.prom"
  slice_file="${OUT_DIR}/context_metrics_${ts}.prom"

  echo "[live-window] sample #${iteration} (${ts})"

  fetched=false
  attempt=1
  while [ "${attempt}" -le "${MAX_RETRIES}" ]; do
    if docker compose exec -T "${SERVICE}" sh -lc "python - <<'PY'
import requests
text = requests.get(\"http://localhost:8000/metrics\", timeout=${REQUEST_TIMEOUT_SECONDS}).text
print(text, end=\"\")
PY" > "${raw_file}"; then
      fetched=true
      break
    fi
    if [ "${attempt}" -lt "${MAX_RETRIES}" ]; then
      sleep "${RETRY_DELAY_SECONDS}"
    fi
    attempt=$((attempt + 1))
  done

  if [ "${fetched}" != "true" ]; then
    echo "[live-window] WARN: sample #${iteration} failed after retries"
    sample_ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    printf '{"timestamp":"%s","iteration":%s,"error":"metrics_fetch_failed"}\n' "${sample_ts}" "${iteration}" >> "${SUMMARY_JSONL}"
    if [ "$(date +%s)" -lt "${end_epoch}" ]; then
      sleep "${INTERVAL_SECONDS}"
    fi
    continue
  fi

  grep -E '^magellan_context_(tokens_total|chars_total|tool_calls_total|tool_call_duration_seconds|route_decisions_total|route_decision_latency_seconds|cache_events_total)' "${raw_file}" > "${slice_file}" || true

  summary_json="$(python3 scripts/summarize_context_metrics.py "${slice_file}" --json)"
  summary_json_compact="$(python3 - <<'PY' "${summary_json}"
import json, sys
print(json.dumps(json.loads(sys.argv[1]), ensure_ascii=False, separators=(",", ":")))
PY
)"
  sample_ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  printf '{"timestamp":"%s","iteration":%s,"summary":%s}\n' "${sample_ts}" "${iteration}" "${summary_json_compact}" >> "${SUMMARY_JSONL}"

  if [ "$(date +%s)" -lt "${end_epoch}" ]; then
    sleep "${INTERVAL_SECONDS}"
  fi
done

echo "[live-window] done. summary file: ${SUMMARY_JSONL}"
