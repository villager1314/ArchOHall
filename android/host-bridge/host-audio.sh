# Sourced by the Android host session launcher, never by the Linux container.
# Foreground mode avoids PulseAudio trying to re-exec /proc/self/exe on Android.
export PULSE_SERVER="unix:$PREFIX/tmp/archohall-pulse.sock"
export PULSE_RUNTIME_PATH="$PREFIX/tmp/archohall-pulse-runtime"
mkdir -p "$PULSE_RUNTIME_PATH"
chmod 700 "$PULSE_RUNTIME_PATH"
if ! pactl info >/dev/null 2>&1; then
    rm -f "$PREFIX/tmp/archohall-pulse.sock"
    pulseaudio -n --daemonize=no --exit-idle-time=-1 --use-pid-file=no \
        --load="module-native-protocol-unix socket=$PREFIX/tmp/archohall-pulse.sock auth-anonymous=1" \
        >"$TASK_DIR/audio.log" 2>&1 &
    pulse_pid=$!
    for ((attempt=0;attempt<50;attempt++)); do
        pactl info >/dev/null 2>&1 && break
        kill -0 "$pulse_pid" 2>/dev/null || break
        sleep 0.1
    done
fi
if pactl info >/dev/null 2>&1; then
    if [[ -z $(pactl list short sinks) ]]; then
        pactl load-module module-aaudio-sink >>"$TASK_DIR/audio.log" 2>&1 || \
            pactl load-module module-sles-sink >>"$TASK_DIR/audio.log" 2>&1 || true
    fi
    if [[ -z $(pactl list short sinks) ]]; then
        echo 'Android audio sink unavailable; see audio.log'
    else
        echo 'Android audio output connected'
    fi
else
    echo 'PulseAudio unavailable; desktop will continue without sound. See audio.log'
fi
