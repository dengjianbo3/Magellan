#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ANDROID_ASSETS_DIR="$FRONTEND_DIR/android/app/src/main/assets/public"
ANDROID_ENV_FILE="$FRONTEND_DIR/.env.android"

cd "$FRONTEND_DIR"

echo "[android-build-web] Cleaning dist and Android bundled assets..."
rm -rf "$FRONTEND_DIR/dist" "$ANDROID_ASSETS_DIR"

npx vite build --mode android
# Android assets merge can fail if compressed sidecar files are included.
find dist -type f \( -name '*.gz' -o -name '*.br' \) -delete
npx cap sync android

INDEX_HTML="$ANDROID_ASSETS_DIR/index.html"
if [ ! -f "$INDEX_HTML" ]; then
  echo "[android-build-web] ERROR: missing $INDEX_HTML after cap sync"
  exit 1
fi

MAIN_JS_REL="$(grep -oE '/assets/js/index-[^"]+\.js' "$INDEX_HTML" | head -n 1)"
if [ -z "${MAIN_JS_REL:-}" ]; then
  echo "[android-build-web] ERROR: unable to locate main index bundle from $INDEX_HTML"
  exit 1
fi

MAIN_JS="$ANDROID_ASSETS_DIR${MAIN_JS_REL}"
if [ ! -f "$MAIN_JS" ]; then
  echo "[android-build-web] ERROR: referenced bundle missing: $MAIN_JS"
  exit 1
fi

if [ -f "$ANDROID_ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ANDROID_ENV_FILE"
  set +a
fi

for expected in "${VITE_API_BASE:-}" "${VITE_AUTH_BASE:-}" "${VITE_WS_BASE:-}" "${VITE_LLM_BASE:-}"; do
  if [ -n "${expected:-}" ] && ! grep -Fq "$expected" "$MAIN_JS"; then
    echo "[android-build-web] ERROR: expected runtime endpoint not found in bundle: $expected"
    echo "[android-build-web] Bundle checked: $MAIN_JS"
    exit 1
  fi
done

echo "[android-build-web] OK: bundle verified ($MAIN_JS_REL)"
