#!/usr/bin/env bash
set -euo pipefail
[[ $(uname -m) == aarch64 ]]
pacman-key --init
pacman-key --populate archlinuxarm
# Only this disposable build sysroot: do not upgrade its unused kernel/firmware.
remove=()
for package in linux-aarch64 linux-firmware; do
    if pacman -Q "$package" >/dev/null 2>&1; then remove+=("$package"); fi
done
if (( ${#remove[@]} )); then pacman -Rns --noconfirm "${remove[@]}"; fi
# Keep CheckSpace enabled; fail with actual filesystem evidence if storage is low.
df -Pk / /var/cache/pacman/pkg
pacman -Syu --needed --noconfirm --disable-sandbox \
    base-devel cmake ninja extra-cmake-modules git pkgconf kwin plasma-mobile \
    qt6-tools qt6-wayland qt6-declarative qt6-5compat qt6-svg \
    wayland-protocols plasma-wayland-protocols vulkan-headers kdoctools \
    libepoxy libpipewire libxcvt libxkbcommon-x11 xcb-util-cursor python
pacman -Q > /out/build-packages.txt
python - <<'PY'
import json, subprocess
expected = json.load(open('/input/package-candidate.json'))['packages']
for name in ('kwin', 'plasma-mobile', 'plasma-workspace', 'qt6-base', 'qt6-declarative', 'qt6-wayland'):
    installed = subprocess.check_output(['pacman', '-Q', name], text=True).split()[1]
    if installed != expected[name]['version']:
        raise SystemExit(f'Package snapshot drift: {name}: {installed}; expected {expected[name]["version"]}')
PY
cmake -S /src -B /build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release '-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG' \
    -DCMAKE_INSTALL_PREFIX=/opt/archohall-mobile -DKDE_INSTALL_LIBDIR=lib \
    -DBUILD_TESTING=OFF -DKWIN_BUILD_KCMS=OFF -DKWIN_BUILD_SCREENLOCKER=OFF \
    -DKWIN_BUILD_GLOBALSHORTCUTS=ON -DKWIN_BUILD_TABBOX=ON \
    -DKWIN_BUILD_ACTIVITIES=ON
cmake --build /build --parallel 4
DESTDIR=/out/staging cmake --install /build
tar -C /out/staging -cJf /out/kwin-6.8.2-anland-arm64-experimental.tar.xz .
sha256sum /out/kwin-6.8.2-anland-arm64-experimental.tar.xz > /out/SHA256SUMS
printf 'Compilation passed. No Android/device validation performed.\n' > /out/COMPILE-PASS.txt
