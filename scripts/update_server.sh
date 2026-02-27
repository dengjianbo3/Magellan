#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/update_server.sh [options]

Options:
  -b, --branch <name>   Git branch to deploy (default: main)
  --no-build            Skip image rebuild (docker compose up -d)
  --service <name>      Restart only one compose service
  --allow-dirty         Allow running with uncommitted local changes
  --dry-run             Print commands only, do not execute
  -h, --help            Show this help

Examples:
  ./scripts/update_server.sh
  ./scripts/update_server.sh --no-build
  ./scripts/update_server.sh --service report_orchestrator
  ./scripts/update_server.sh --branch dev --dry-run
EOF
}

BRANCH="main"
NO_BUILD="0"
SERVICE=""
ALLOW_DIRTY="0"
DRY_RUN="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -b|--branch)
      BRANCH="${2:-}"
      shift 2
      ;;
    --no-build)
      NO_BUILD="1"
      shift
      ;;
    --service)
      SERVICE="${2:-}"
      shift 2
      ;;
    --allow-dirty)
      ALLOW_DIRTY="1"
      shift
      ;;
    --dry-run)
      DRY_RUN="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[update_server] Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

if ! command -v git >/dev/null 2>&1; then
  echo "[update_server] git is required"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[update_server] docker compose is required"
  exit 1
fi

if [[ "$ALLOW_DIRTY" != "1" ]] && [[ -n "$(git status --porcelain)" ]]; then
  echo "[update_server] Working tree is not clean. Commit/stash first or use --allow-dirty."
  exit 1
fi

run_cmd() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] $*"
  else
    echo "[run] $*"
    "$@"
  fi
}

echo "[update_server] Deploying branch: $BRANCH"
run_cmd git fetch origin
run_cmd git checkout "$BRANCH"
run_cmd git pull --ff-only origin "$BRANCH"

if [[ "$NO_BUILD" == "1" ]]; then
  if [[ -n "$SERVICE" ]]; then
    run_cmd docker compose up -d "$SERVICE"
  else
    run_cmd docker compose up -d
  fi
else
  if [[ -n "$SERVICE" ]]; then
    run_cmd docker compose up -d --build "$SERVICE"
  else
    run_cmd docker compose up -d --build
  fi
fi

run_cmd docker compose ps
echo "[update_server] Done"
