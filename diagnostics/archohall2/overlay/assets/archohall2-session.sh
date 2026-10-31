#!/usr/bin/env bash
set -euo pipefail
export HOME=/home/arch USER=arch LOGNAME=arch
export XDG_RUNTIME_DIR=/run/user/1000
export XDG_CURRENT_DESKTOP=KDE XDG_SESSION_DESKTOP=KDE XDG_SESSION_TYPE=wayland
export PLASMA_PLATFORM=phone XDG_MENU_PREFIX=plasma-
export QT_QPA_PLATFORM=wayland QSG_RHI_BACKEND=opengl
export XDG_DATA_DIRS=/opt/archohall-mobile/share:/usr/local/share:/usr/share
export QML_IMPORT_PATH=/opt/archohall-mobile/lib/qt6/qml
export QT_PLUGIN_PATH=/opt/archohall-mobile/lib/qt6/plugins
unset QT_QUICK_BACKEND
export LD_LIBRARY_PATH=/opt/archohall-mobile/lib
export LIBGL_DRIVERS_PATH=/opt/archohall-mobile/lib/dri
export __EGL_VENDOR_LIBRARY_FILENAMES=/opt/archohall-mobile/share/glvnd/egl_vendor.d/50_mesa.json
export LD_PRELOAD=/opt/archohall-mobile/lib/drmshim.so
export KWIN_DRM_DEVICES=/dev/dri/renderD128
state=/var/lib/localdesktop/session
mkdir -p "$state"
fail() { printf 'reason=ArchOHall2 session failed (exit %s)\n' "$1" > "$state/plasma-failed"; }
trap 'fail "$?"' ERR
[[ -S ${ANLAND_SOCKET:?Android display transport is missing} ]]
[[ -r /opt/archohall-mobile/lib/dri/kgsl_dri.so ]]
cd "$HOME"
# Use a fresh socket name, avoiding stale locks without unlinking live sockets.
exec dbus-run-session -- /opt/archohall-mobile/bin/kwin_wayland \
    --anland --no-lockscreen --socket "wayland-archohall2-$$" \
    --exit-with-session /usr/local/bin/archohall2-mobile-shell
