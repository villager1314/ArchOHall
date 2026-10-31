#!/usr/bin/env bash
set -euo pipefail
state=/var/lib/localdesktop/session
trap 'printf "reason=Plasma Mobile exited (status %s)\n" "$?" > "$state/plasma-failed"' ERR
scale=$(cat /etc/archohall2/output-scale 2>/dev/null || echo 1.5)
# Run this on the compositor-created session bus and Wayland connection.
if command -v kscreen-doctor >/dev/null; then
    output=$(kscreen-doctor -o | sed -nE 's/^[[:space:]]*Output: ([0-9]+).*/\1/p' | head -n 1)
    if [[ -n $output ]]; then kscreen-doctor "output.$output.scale.$scale" || true; fi
fi
export XDG_DATA_DIRS=/opt/archohall-mobile/share:/usr/local/share:/usr/share
export QML_IMPORT_PATH=/opt/archohall-mobile/lib/qt6/qml
export QT_PLUGIN_PATH=/opt/archohall-mobile/lib/qt6/plugins
/usr/bin/plasmashell -p org.kde.plasma.mobileshell &
shell_pid=$!
trap 'kill -TERM "$shell_pid" 2>/dev/null || true; wait "$shell_pid" 2>/dev/null || true; exit 143' TERM INT
wait "$shell_pid"
