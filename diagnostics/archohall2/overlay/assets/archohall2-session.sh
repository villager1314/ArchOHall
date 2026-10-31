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
unset QT_QUICK_BACKEND LIBGL_ALWAYS_SOFTWARE GALLIUM_DRIVER EGL_PLATFORM
export MESA_LOADER_DRIVER_OVERRIDE=kgsl GALLIUM_DRIVER=freedreno
export FD_FORCE_KGSL=1 FD_KGSL_ENABLE_DMABUF=1 TURNIP_KMD=kgsl
export ANLAND=1 XWAYLAND_FORCE_KGSL_SURFACELESS=1
export LD_LIBRARY_PATH=/opt/archohall-mobile/lib
export LIBGL_DRIVERS_PATH=/opt/archohall-mobile/lib/dri
export __EGL_VENDOR_LIBRARY_FILENAMES=/opt/archohall-mobile/share/glvnd/egl_vendor.d/50_mesa.json
export LD_PRELOAD=/opt/archohall-mobile/lib/drmshim.so
export KWIN_DRM_DEVICES=/dev/dri/renderD128
state=/var/lib/localdesktop/session
mkdir -p "$state"
# The APK clears stale attempt markers before launching. Only Android's native
# fenced-frame readiness callback may confirm a successful desktop/GPU trial.
exec >> "$state/session.log" 2>&1
printf 'stage=session-start timestamp=%s\n' "$(date -Iseconds)"
fail() { printf 'reason=ArchOHall2 session failed (exit %s)\n' "$1" > "$state/plasma-failed"; }
trap 'fail "$?"' ERR
/usr/local/bin/archohall2-gpu-check
cd "$HOME"
# Fresh socket names avoid stale locks without unlinking another live compositor.
# Keep this supervisor alive: ERR traps do not survive an exec.
child=
stop() { if [[ -n $child ]]; then kill -TERM -- "-$child" 2>/dev/null || true; wait "$child" 2>/dev/null || true; fi; }
trap 'stop; exit 143' TERM
trap 'stop; exit 130' INT
setsid dbus-run-session -- /opt/archohall-mobile/bin/kwin_wayland \
    --anland --no-lockscreen --socket "wayland-archohall2-$$" \
    --exit-with-session /usr/local/bin/archohall2-mobile-shell &
child=$!
status=0
wait "$child" || status=$?
printf 'stage=session-exit status=%s\n' "$status"
if (( status != 0 )); then fail "$status"; fi
exit "$status"
