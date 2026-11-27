#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Android/Sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
mkdir -p "$ANDROID_HOME"
cd "$ROOT"
apt-get update -qq
apt-get install -y -qq openjdk-17-jdk wget unzip
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export PATH="$JAVA_HOME/bin:$PATH"
if [ ! -x "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" ]; then
  mkdir -p "$ANDROID_HOME/cmdline-tools/latest"
  wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O /tmp/android-cmdline-tools.zip
  mkdir -p /tmp/android-cmdline-tools
  unzip -q /tmp/android-cmdline-tools.zip -d /tmp/android-cmdline-tools
  cp -R /tmp/android-cmdline-tools/cmdline-tools/. "$ANDROID_HOME/cmdline-tools/latest/"
fi
SDKMANAGER="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
yes | "$SDKMAN" --licenses >/dev/null
"$SDKMAN" "platform-tools" "platforms;android-35" "build-tools;35.0.0"
if ! command -v gradle >/dev/null 2>&1 || ! gradle --version | grep -q 'Gradle 8.9'; then
  wget -q https://services.gradle.org/distributions/gradle-8.9-bin.zip -O /tmp/gradle-8.9.zip
  rm -rf /opt/gradle-8.9
  unzip -q /tmp/gradle-8.9.zip -d /opt
  export PATH="/opt/gradle-8.9/bin:$PATH"
fi
node tests_store_parser.js
gradle --no-daemon assembleDebug
cp app/build/outputs/apk/debug/app-debug.apk "$ROOT/PRICE_RADAR_1.2.2_debug.apk"
echo "APK: $ROOT/PRICE_RADAR_1.2.2_debug.apk"
