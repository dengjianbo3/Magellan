#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ANDROID_DIR="$FRONTEND_DIR/android"
APP_GRADLE_FILE="$ANDROID_DIR/app/build.gradle"
APK_OUTPUT_DIR="$ANDROID_DIR/app/build/outputs/apk/debug"
DEFAULT_APK="$APK_OUTPUT_DIR/app-debug.apk"

if [ -z "${JAVA_HOME:-}" ] && [ -d "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home" ]; then
  export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
fi
if [ -d "/opt/homebrew/opt/openjdk@17/bin" ]; then
  export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"
fi
if [ -z "${ANDROID_HOME:-}" ] && [ -d "/opt/homebrew/share/android-commandlinetools" ]; then
  export ANDROID_HOME="/opt/homebrew/share/android-commandlinetools"
fi
if [ -z "${ANDROID_SDK_ROOT:-}" ] && [ -n "${ANDROID_HOME:-}" ]; then
  export ANDROID_SDK_ROOT="$ANDROID_HOME"
fi

export GRADLE_USER_HOME="$FRONTEND_DIR/.gradle"

cd "$ANDROID_DIR"
./gradlew assembleDebug

if [ ! -f "$DEFAULT_APK" ]; then
  echo "[android-apk-debug] ERROR: missing default APK: $DEFAULT_APK"
  exit 1
fi

VERSION_NAME="$(sed -n 's/^[[:space:]]*versionName[[:space:]]*\"\([^\"]*\)\"/\1/p' "$APP_GRADLE_FILE" | head -n 1)"
VERSION_CODE="$(sed -n 's/^[[:space:]]*versionCode[[:space:]]*\([0-9][0-9]*\)/\1/p' "$APP_GRADLE_FILE" | head -n 1)"
BUILD_TS="$(date +%Y%m%d%H%M%S)"

if [ -z "${VERSION_NAME:-}" ]; then
  VERSION_NAME="unknown"
fi
if [ -z "${VERSION_CODE:-}" ]; then
  VERSION_CODE="0"
fi

VERSIONED_APK="$APK_OUTPUT_DIR/magellan-v${VERSION_NAME}-b${VERSION_CODE}-${BUILD_TS}.apk"
cp -f "$DEFAULT_APK" "$VERSIONED_APK"
echo "[android-apk-debug] APK: $VERSIONED_APK"
shasum -a 256 "$VERSIONED_APK"
