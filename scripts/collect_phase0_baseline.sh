#!/usr/bin/env bash
set -euo pipefail

METRICS_URL="${1:-http://localhost:18000/metrics}"
OUT_DIR="${2:-./tmp/phase0_baseline}"
TS="$(date +"%Y%m%d_%H%M%S")"
MAX_TIME_SECONDS="${MAX_TIME_SECONDS:-90}"
MAX_RETRIES="${MAX_RETRIES:-3}"
RETRY_DELAY_SECONDS="${RETRY_DELAY_SECONDS:-2}"

mkdir -p "${OUT_DIR}"

RAW_FILE="${OUT_DIR}/metrics_${TS}.prom"
SLICE_FILE="${OUT_DIR}/context_metrics_${TS}.prom"

echo "[phase0] pulling metrics from ${METRICS_URL}"
attempt=1
while true; do
  if curl -fsS --max-time "${MAX_TIME_SECONDS}" "${METRICS_URL}" -o "${RAW_FILE}"; then
    break
  fi
  if [ "${attempt}" -ge "${MAX_RETRIES}" ]; then
    echo "[phase0] failed to pull metrics after ${attempt} attempts" >&2
    exit 1
  fi
  attempt=$((attempt + 1))
  sleep "${RETRY_DELAY_SECONDS}"
done

grep -E '^magellan_context_(tokens_total|chars_total|tool_calls_total|tool_call_duration_seconds|route_decisions_total|route_decision_latency_seconds|cache_events_total)' "${RAW_FILE}" > "${SLICE_FILE}" || true

echo "[phase0] raw metrics: ${RAW_FILE}"
echo "[phase0] context metrics slice: ${SLICE_FILE}"
