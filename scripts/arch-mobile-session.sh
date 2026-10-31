#!/usr/bin/env bash
# Experimental guest entry point. Requires an Arch-built Anland KWin stack.
set -euo pipefail
if [[ ! -r /etc/arch-release ]]; then
    echo 'This entry point requires an Arch guest.' >&2
    exit 1
fi
if [[ -z ${ANLAND_SOCKET:-} || ! -S $ANLAND_SOCKET ]]; then
    echo 'Start the Portal Android Anland host and supply ANLAND_SOCKET first.' >&2
    exit 1
fi
if [[ ${LD_LIBRARY_PATH:-} == *kwin-anland-arm64* || ${LD_LIBRARY_PATH:-} == *kwin-debian-arm64* ]]; then
    echo 'Refusing the Debian KWin library overlay in an Arch guest.' >&2
    exit 1
fi
kwin=/opt/archohall-mobile/bin/kwin_wayland
if ! "$kwin" --help 2>/dev/null | grep -q -- '--anland'; then
    echo 'An Arch-built KWin advertising --anland is required; stock KWin is insufficient.' >&2
    exit 1
fi
[[ -n ${XDG_RUNTIME_DIR:-} && -d $XDG_RUNTIME_DIR ]] || {
    echo 'Supply a private XDG_RUNTIME_DIR from the runtime.' >&2; exit 1;
}
[[ $(stat -c %a "$XDG_RUNTIME_DIR") == 700 ]] || {
    echo 'XDG_RUNTIME_DIR must have mode 700.' >&2; exit 1;
}
export QT_QPA_PLATFORM=wayland XDG_CURRENT_DESKTOP=KDE XDG_SESSION_TYPE=wayland
export PLASMA_PLATFORM=phone XDG_SESSION_DESKTOP=KDE XDG_MENU_PREFIX=plasma-
# Keep the host-selected Mesa driver and transport configuration.
exec dbus-run-session -- "$kwin" --anland --no-lockscreen \
    --socket "wayland-archohall-mobile-$$" \
    --exit-with-session '/usr/bin/plasmashell -p org.kde.plasma.mobileshell'
