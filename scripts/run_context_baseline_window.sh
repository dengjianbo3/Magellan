#!/usr/bin/env bash
set -euo pipefail

DURATION_MINUTES="${DURATION_MINUTES:-30}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-120}"
METRICS_URL="${METRICS_URL:-http://localhost:18000/metrics}"
OUT_DIR="${OUT_DIR:-./tmp/phase0_baseline_window}"

mkdir -p "${OUT_DIR}"
SUMMARY_JSONL="${OUT_DIR}/summary.jsonl"
: > "${SUMMARY_JSONL}"

end_epoch=$(( $(date +%s) + DURATION_MINUTES * 60 ))
iteration=0

echo "[window] duration=${DURATION_MINUTES}m interval=${INTERVAL_SECONDS}s metrics=${METRICS_URL}"
echo "[window] output=${OUT_DIR}"

while [ "$(date +%s)" -lt "${end_epoch}" ]; do
  iteration=$((iteration + 1))
  echo "[window] sample #${iteration}"

  ./scripts/collect_phase0_baseline.sh "${METRICS_URL}" "${OUT_DIR}"

  latest_slice="$(ls -1t "${OUT_DIR}"/context_metrics_*.prom | head -n 1)"
  summary_json="$(python3 scripts/summarize_context_metrics.py "${latest_slice}" --json)"
  summary_json_compact="$(python3 - <<'PY' "${summary_json}"
import json, sys
print(json.dumps(json.loads(sys.argv[1]), ensure_ascii=False, separators=(",", ":")))
PY
)"
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  printf '{"timestamp":"%s","iteration":%s,"summary":%s}\n' "${ts}" "${iteration}" "${summary_json_compact}" >> "${SUMMARY_JSONL}"

  if [ "$(date +%s)" -lt "${end_epoch}" ]; then
    sleep "${INTERVAL_SECONDS}"
  fi
done

echo "[window] done. summary file: ${SUMMARY_JSONL}"
