#!/usr/bin/env bash
# Build a signed Next PMS release APK.
#
# Secrets come from the gitignored env file written when the keystore was created:
#   android-capacitor/keystore/SECRET-DO-NOT-COMMIT.env
# (or export PMS_KEYSTORE_PATH / PMS_KEYSTORE_PW / PMS_KEY_PW / PMS_KEY_ALIAS yourself).
#
# Usage:  bash scripts/build-apk.sh [version]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SECRET_ENV="$REPO_ROOT/android-capacitor/keystore/SECRET-DO-NOT-COMMIT.env"

if [[ -f "$SECRET_ENV" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$SECRET_ENV"; set +a
  # the env file uses KEYSTORE=; map to PMS_KEYSTORE_PATH
  export PMS_KEYSTORE_PATH="${PMS_KEYSTORE_PATH:-${KEYSTORE:-}}"
fi

export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
: "${PMS_KEYSTORE_PATH:?set PMS_KEYSTORE_PATH (or provide SECRET-DO-NOT-COMMIT.env)}"
: "${PMS_KEYSTORE_PW:?set PMS_KEYSTORE_PW}"
: "${PMS_KEY_PW:?set PMS_KEY_PW}"
: "${PMS_KEY_ALIAS:?set PMS_KEY_ALIAS}"
VERSION="${1:-1.0.0}"

echo "▶ Native web build"
( cd "$REPO_ROOT/frontend" && yarn build:native )

echo "▶ cap copy android"
( cd "$REPO_ROOT/android-capacitor" && npx cap copy android )

echo "▶ assembleRelease"
( cd "$REPO_ROOT/android-capacitor/android" && ./gradlew assembleRelease --no-daemon )

SRC="$REPO_ROOT/android-capacitor/android/app/build/outputs/apk/release/app-release.apk"
mkdir -p "$REPO_ROOT/dist-apk"
DEST="$REPO_ROOT/dist-apk/next-pms-${VERSION}.apk"
cp "$SRC" "$DEST"

echo ""
echo "✅ Signed APK: $DEST"
echo "   Verify: \$ANDROID_HOME/build-tools/*/apksigner verify --print-certs \"$DEST\""
echo "   Install: adb install -r \"$DEST\""
