#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$FRONTEND_DIR"

npm run build
# Android assets merge can fail if compressed sidecar files are included.
find dist -type f \( -name '*.gz' -o -name '*.br' \) -delete
npx cap sync android
