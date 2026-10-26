#!/data/data/com.termux/files/usr/bin/bash
# Host-side launcher for stock Termux; integrated APKs must adapt the shebang.
set -euo pipefail
export DISPLAY="${DISPLAY:-:0}"
command -v termux-x11 >/dev/null
command -v proot-distro >/dev/null
command -v xdpyinfo >/dev/null || { echo 'Install xorg-xdpyinfo in Termux.' >&2; exit 1; }
if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    termux-x11 "$DISPLAY" >/dev/null 2>&1 &
    ready=0
    for ((attempt=0; attempt<30; attempt++)); do
        if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then ready=1; break; fi
        sleep 0.2
    done
    (( ready == 1 )) || { echo 'Termux:X11 did not become ready.' >&2; exit 1; }
fi
am start --user 0 -n com.termux.x11/com.termux.x11.MainActivity >/dev/null
# Audio is optional. Never expose an anonymous TCP listener to the LAN.
if command -v pulseaudio >/dev/null; then
    pulseaudio --start --exit-idle-time=-1
    if ! pactl list short modules | grep -q 'module-native-protocol-tcp.*port=4713'; then
        pactl load-module module-native-protocol-tcp listen=127.0.0.1 port=4713 auth-ip-acl=127.0.0.1 >/dev/null
    fi
fi
proot-distro login "${ARCHOHALL_CONTAINER:-archohall}" -- /usr/local/bin/archohall-init
exec proot-distro login "${ARCHOHALL_CONTAINER:-archohall}" --user arch --shared-tmp -- \
    /usr/bin/env DISPLAY="$DISPLAY" PULSE_SERVER=tcp:127.0.0.1:4713 \
    ARCHOHALL_RENDERER="${ARCHOHALL_RENDERER:-software}" \
    ARCHOHALL_WIDTH="${ARCHOHALL_WIDTH:-720}" ARCHOHALL_HEIGHT="${ARCHOHALL_HEIGHT:-1280}" \
    /usr/local/bin/archohall-mobile
