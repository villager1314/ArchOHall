# Sourced by the Android host session launcher, never by the Linux container.
# Foreground mode avoids PulseAudio trying to re-exec /proc/self/exe on Android.
export PULSE_SERVER="unix:$PREFIX/tmp/archohall-pulse.sock"
export PULSE_RUNTIME_PATH="$PREFIX/tmp/archohall-pulse-runtime"
mkdir -p "$PULSE_RUNTIME_PATH"
chmod 700 "$PULSE_RUNTIME_PATH"
if ! pactl info >/dev/null 2>&1; then
    rm -f "$PREFIX/tmp/archohall-pulse.sock"
    pulseaudio -n --daemonize=no --exit-idle-time=-1 --use-pid-file=no \
        --disable-shm=yes \
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

# Guest connections use authenticated loopback TCP. This avoids Unix peer-UID
# and shared-memory assumptions across PRoot's simulated identity boundary.
export ARCHOHALL_GUEST_PULSE_SERVER=''
umask 077
head -c 256 /dev/urandom > "$TASK_DIR/pulse-cookie"
export PULSE_COOKIE="$TASK_DIR/pulse-cookie"
if pactl info >/dev/null 2>&1; then
    for port in {47130..47140}; do
        if pactl load-module module-native-protocol-tcp \
            listen=127.0.0.1 port="$port" auth-anonymous=0 \
            auth-cookie-enabled=1 auth-cookie="$PULSE_COOKIE" >>"$TASK_DIR/audio.log" 2>&1; then
            export ARCHOHALL_GUEST_PULSE_SERVER="tcp:127.0.0.1:$port"
            break
        fi
    done
    sink=$(pactl list short sinks | awk 'NR==1 {print $2}')
    if [[ -n $sink ]]; then
        pactl set-default-sink "$sink" >>"$TASK_DIR/audio.log" 2>&1 || true
        pactl set-sink-mute "$sink" 0 >>"$TASK_DIR/audio.log" 2>&1 || true
    fi
fi
if [[ -n $ARCHOHALL_GUEST_PULSE_SERVER ]]; then
    {
        printf 'PULSE_SERVER=%s\n' "$ARCHOHALL_GUEST_PULSE_SERVER"
        printf 'PULSE_COOKIE=/tmp/archohall-pulse-cookie\n'
    } > "$HOST_BRIDGE/audio.env.tmp"
    mv "$HOST_BRIDGE/audio.env.tmp" "$HOST_BRIDGE/audio.env"
    echo 'Authenticated guest audio transport ready'
else
    rm -f "$HOST_BRIDGE/audio.env"
    echo 'Guest audio transport unavailable; see audio.log'
fi
