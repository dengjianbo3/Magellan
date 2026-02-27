#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ANDROID_DIR="$FRONTEND_DIR/android"

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
