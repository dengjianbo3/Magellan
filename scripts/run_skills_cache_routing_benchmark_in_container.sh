#!/usr/bin/env bash
set -euo pipefail

SERVICE="${SERVICE:-report_orchestrator}"
LATENCY="${LATENCY:-0.2}"
JSON_FLAG="${JSON_FLAG:---json}"

SCRIPT_PATH="scripts/run_skills_cache_routing_benchmark.py"

if [ ! -f "${SCRIPT_PATH}" ]; then
  echo "[benchmark] script not found: ${SCRIPT_PATH}" >&2
  exit 1
fi

cat "${SCRIPT_PATH}" | docker compose exec -T "${SERVICE}" sh -lc "python - --latency ${LATENCY} ${JSON_FLAG}"

