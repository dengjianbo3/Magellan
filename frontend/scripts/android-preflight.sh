#!/usr/bin/env bash
set -euo pipefail

red='\033[0;31m'
green='\033[0;32m'
yellow='\033[1;33m'
reset='\033[0m'

ok() { echo -e "${green}OK${reset}  $1"; }
warn() { echo -e "${yellow}WARN${reset}  $1"; }
fail() { echo -e "${red}FAIL${reset}  $1"; }

pass=true
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ANDROID_DIR="$FRONTEND_DIR/android"

# Auto-detect Homebrew JDK 17 if JAVA_HOME is not set.
if [ -z "${JAVA_HOME:-}" ] && [ -d "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home" ]; then
  export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
  export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"
fi

# Auto-detect Android SDK path.
if [ -z "${ANDROID_HOME:-}" ] && [ -d "/opt/homebrew/share/android-commandlinetools" ]; then
  export ANDROID_HOME="/opt/homebrew/share/android-commandlinetools"
fi
if [ -z "${ANDROID_HOME:-}" ] && [ -d "$HOME/Library/Android/sdk" ]; then
  export ANDROID_HOME="$HOME/Library/Android/sdk"
fi
if [ -z "${ANDROID_SDK_ROOT:-}" ] && [ -n "${ANDROID_HOME:-}" ]; then
  export ANDROID_SDK_ROOT="$ANDROID_HOME"
fi

echo "[Android Preflight]"
echo

if command -v node >/dev/null 2>&1; then
  ok "Node: $(node -v)"
else
  fail "Node.js not found"
  pass=false
fi

if command -v npm >/dev/null 2>&1; then
  ok "npm: $(npm -v)"
else
  fail "npm not found"
  pass=false
fi

if command -v java >/dev/null 2>&1; then
  set +e
  jv=$(java -version 2>&1 | head -n 1)
  java_status=$?
  set -e
  if [ $java_status -eq 0 ]; then
    ok "Java: ${jv}"
  else
    fail "Java runtime command exists but is not usable: ${jv}"
    pass=false
  fi
else
  fail "Java runtime not found (need JDK 17+)"
  pass=false
fi

if command -v javac >/dev/null 2>&1; then
  set +e
  jcv=$(javac -version 2>&1)
  javac_status=$?
  set -e
  if [ $javac_status -eq 0 ]; then
    ok "javac: ${jcv}"
  else
    fail "javac command exists but is not usable: ${jcv}"
    pass=false
  fi
else
  fail "javac not found (need full JDK)"
  pass=false
fi

if [ -n "${JAVA_HOME:-}" ]; then
  ok "JAVA_HOME=$JAVA_HOME"
else
  warn "JAVA_HOME is not set (recommended to set it)"
fi

if [ -n "${ANDROID_HOME:-}" ] || [ -n "${ANDROID_SDK_ROOT:-}" ]; then
  ok "Android SDK env present (ANDROID_HOME/ANDROID_SDK_ROOT)"
else
  warn "ANDROID_HOME/ANDROID_SDK_ROOT not set (Android Studio usually manages this)"
fi

if [ -d "$ANDROID_DIR" ]; then
  ok "Android project exists: $ANDROID_DIR"
else
  fail "Android project not found; run: cd frontend && npx cap add android"
  pass=false
fi

if [ -f "$ANDROID_DIR/gradlew" ]; then
  ok "Gradle wrapper found"
  if command -v java >/dev/null 2>&1; then
    export GRADLE_USER_HOME="$FRONTEND_DIR/.gradle"
    set +e
    gv=$(cd "$ANDROID_DIR" && ./gradlew -version 2>&1)
    status=$?
    set -e
    if [ $status -eq 0 ]; then
      ok "Gradle wrapper runnable"
    else
      fail "Gradle wrapper failed. Output:"
      echo "$gv" | sed 's/^/  /'
      pass=false
    fi
  fi
else
  fail "Gradle wrapper missing: $ANDROID_DIR/gradlew"
  pass=false
fi

echo
if [ "$pass" = true ]; then
  ok "Preflight passed"
  exit 0
else
  echo
  echo "Suggested fix (macOS):"
  echo "  brew install openjdk@17"
  echo "  export JAVA_HOME=\$(/usr/libexec/java_home -v 17)"
  echo "  export PATH=\"\$JAVA_HOME/bin:\$PATH\""
  fail "Preflight failed"
  exit 1
fi
