#!/usr/bin/env bash
set -euo pipefail
task_android_sdk="${ANDROID_HOME:-${RUNNER_TEMP:-/tmp}/archohall-android-sdk}"
sdk_manager="$task_android_sdk/cmdline-tools/latest/bin/sdkmanager"
if [[ ! -x $sdk_manager ]]; then
    mkdir -p "$task_android_sdk/cmdline-tools"
    sdk_archive=$(mktemp)
    sdk_unpack=$(mktemp -d)
    curl -fL --retry 4 --connect-timeout 30 --max-time 600 \
        https://dl.google.com/android/repository/commandlinetools-linux-13114758_latest.zip -o "$sdk_archive"
    echo "7ec965280a073311c339e571cd5de778b9975026cfcbe79f2b1cdcb1e15317ee  $sdk_archive" | sha256sum -c -
    unzip -q "$sdk_archive" -d "$sdk_unpack"
    mv "$sdk_unpack/cmdline-tools" "$task_android_sdk/cmdline-tools/latest"
    rm -f "$sdk_archive"
    rmdir "$sdk_unpack"
fi
"$sdk_manager" --sdk_root="$task_android_sdk" --licenses < <(yes) >/dev/null
"$sdk_manager" --sdk_root="$task_android_sdk" 'platforms;android-36' 'build-tools;36.0.0'
if [[ -n ${GITHUB_ENV:-} ]]; then
    printf 'ANDROID_HOME=%s\nANDROID_SDK_ROOT=%s\n' "$task_android_sdk" "$task_android_sdk" >> "$GITHUB_ENV"
fi
printf 'Android SDK: %s\n' "$task_android_sdk"
