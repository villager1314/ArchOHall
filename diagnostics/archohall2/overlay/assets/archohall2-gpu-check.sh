#!/usr/bin/env bash
# Runs INSIDE the guest; host-side ldd cannot validate ARM/glibc libraries.
set -euo pipefail
stage=environment
trap 'printf "stage=%s status=failed exit=%s line=%s\n" "$stage" "$?" "$LINENO" >&2' ERR
[[ ${QT_QPA_PLATFORM:-} == wayland && ${QSG_RHI_BACKEND:-} == opengl ]]
[[ ${MESA_LOADER_DRIVER_OVERRIDE:-} == kgsl && ${GALLIUM_DRIVER:-} == freedreno ]]
[[ ${FD_FORCE_KGSL:-} == 1 && ${FD_KGSL_ENABLE_DMABUF:-} == 1 && ${TURNIP_KMD:-} == kgsl ]]
[[ -z ${QT_QUICK_BACKEND:-} && ${LIBGL_ALWAYS_SOFTWARE:-0} != 1 ]]
[[ ${KWIN_RENDER_NODES:-} == /dev/dri/renderD128 && -z ${KWIN_DRM_DEVICES:-} ]]
stage=devices
[[ -r /dev/kgsl-3d0 && -w /dev/kgsl-3d0 ]]
[[ -S ${ANLAND_SOCKET:?Android display socket is missing} ]]
[[ -d $XDG_RUNTIME_DIR && -O $XDG_RUNTIME_DIR && -w $XDG_RUNTIME_DIR ]]
[[ $(stat -c %a "$XDG_RUNTIME_DIR") == 700 ]]
stage=libraries
for library in /opt/archohall-mobile/lib/dri/kgsl_dri.so /opt/archohall-mobile/lib/drmshim.so /opt/archohall-mobile/lib/libEGL_mesa.so.0 /opt/archohall-mobile/lib/libgbm.so.1 /opt/archohall-mobile/bin/kwin_wayland /usr/local/bin/wl-copy /usr/local/bin/wl-paste /usr/local/lib/portal/anland-damage-68.so; do
    [[ -s $library ]]
    dependencies=$(ldd "$library" 2>&1)
    printf '%s\n%s\n' "$library" "$dependencies"
    if grep -q 'not found' <<< "$dependencies"; then exit 1; fi
done
stage=kwin-backend
help=$(QT_QPA_PLATFORM=offscreen /opt/archohall-mobile/bin/kwin_wayland --help 2>&1)
for option in --anland --inputmethod --exit-with-session; do
    if ! grep -qF -- "$option" <<< "$help"; then
        printf 'stage=kwin-options status=failed missing=%s\n' "$option" >&2
        exit 1
    fi
done
for executable in setsid dbus-run-session plasmashell kscreen-doctor; do command -v "$executable"; done
printf 'stage=preflight status=passed (not desktop-rendering proof)\n'
