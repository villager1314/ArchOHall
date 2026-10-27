#!/usr/bin/env bash
set -euo pipefail
pacman-key --init
pacman-key --populate archlinuxarm
remove_packages=()
for package in linux-aarch64 linux-firmware; do
    if pacman -Q "$package" >/dev/null 2>&1; then remove_packages+=("$package"); fi
done
if (( ${#remove_packages[@]} )); then pacman -Rns --noconfirm "${remove_packages[@]}"; fi
pacman -Syu --noconfirm --needed base-devel cmake ninja extra-cmake-modules \
    kwin qt6-tools qt6-5compat qt6-wayland qt6-svg qt6-declarative \
    wayland-protocols plasma-wayland-protocols vulkan-headers kdoctools \
    python xorg-server-xvfb xorg-xdpyinfo wayland-utils
source_commit=ab7df7ccb7c6af20f4b279cd6220f7cd3d2267d7
curl --fail --location --retry 3 --proto '=https' --proto-redir '=https' \
    "https://codeload.github.com/KDE/kwin/tar.gz/$source_commit" -o /tmp/kwin-source.tar.gz
mkdir -p /build/kwin
tar -xzf /tmp/kwin-source.tar.gz --strip-components=1 -C /build/kwin
python /opt/compat-build/patch-kwin.py /build/kwin
cmake -S /build/kwin -B /build/output -G Ninja \
    -DCMAKE_INSTALL_PREFIX=/opt/archohall-kwin-compat \
    -DKDE_INSTALL_LIBDIR=lib \
    -DKDE_INSTALL_PLUGINDIR=lib/qt6/plugins \
    -DKDE_INSTALL_QMLDIR=lib/qt6/qml \
    -DCMAKE_INSTALL_RPATH=/opt/archohall-kwin-compat/lib \
    -DCMAKE_BUILD_TYPE=Release '-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG' \
    -DBUILD_TESTING=OFF -DKWIN_BUILD_KCMS=OFF -DKWIN_BUILD_SCREENLOCKER=OFF \
    -DKWIN_BUILD_NOTIFICATIONS=OFF -DKWIN_BUILD_RUNNERS=OFF \
    -DKWIN_BUILD_GLOBALSHORTCUTS=OFF \
    -DKWIN_BUILD_DECORATIONS=OFF -DKWIN_BUILD_TABBOX=OFF \
    -DKWIN_BUILD_ACTIVITIES=OFF
cmake --build /build/output --parallel 4
cmake --install /build/output --strip
install -Dm755 /opt/compat-build/archohall-kwin-compat /usr/local/bin/archohall-kwin-compat
pacman -Q > /opt/archohall-kwin-compat/build-packages.txt
printf '%s\n' "$source_commit" > /opt/archohall-kwin-compat/upstream-commit.txt
cp /build/kwin/COPYING* /opt/archohall-kwin-compat/ 2>/dev/null || true
cp -a /build/kwin/LICENSES /opt/archohall-kwin-compat/
cp /opt/compat-build/patch-kwin.py /opt/archohall-kwin-compat/
