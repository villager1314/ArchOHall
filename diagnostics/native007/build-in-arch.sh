#!/usr/bin/env bash
set -euo pipefail
pacman -S --needed --noconfirm base-devel cmake ninja extra-cmake-modules qt6-tools qt6-5compat qt6-svg wayland-protocols plasma-wayland-protocols vulkan-headers kdoctools xorg-server-xvfb wayland-utils
version=$(pacman -Q kwin | awk '{print $2}' | cut -d- -f1)
[[ $version == 6.8.1 ]] || { echo "Native patch requires KWin 6.8.1; repository has $version. Refusing ABI mismatch."; exit 1; }
curl -fL --retry 4 https://codeload.github.com/KDE/kwin/tar.gz/1b798c05c19b1124edb1e16623191fcd2c128fd0 -o /tmp/kwin-native-source.tar.gz
mkdir -p /build/native-kwin
tar -xzf /tmp/kwin-native-source.tar.gz --strip-components=1 -C /build/native-kwin
python3 /opt/native007/patch-kwin.py /build/native-kwin
cmake -S /build/native-kwin -B /build/native-output -G Ninja \
 -DCMAKE_INSTALL_PREFIX=/opt/archohall-kwin-compat -DKDE_INSTALL_LIBDIR=lib \
 -DKDE_INSTALL_PLUGINDIR=lib/qt6/plugins -DKDE_INSTALL_QMLDIR=lib/qt6/qml \
 -DCMAKE_INSTALL_RPATH=/opt/archohall-kwin-compat/lib -DCMAKE_BUILD_TYPE=Release \
 '-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG' -DBUILD_TESTING=OFF \
 -DKWIN_BUILD_KCMS=OFF -DKWIN_BUILD_SCREENLOCKER=OFF -DKWIN_BUILD_NOTIFICATIONS=OFF -DKWIN_BUILD_RUNNERS=OFF \
 -DKWIN_BUILD_GLOBALSHORTCUTS=ON -DKWIN_BUILD_TABBOX=ON -DKWIN_BUILD_ACTIVITIES=ON
cmake --build /build/native-output --parallel 4
cmake --install /build/native-output --strip
install -Dm755 /opt/native007/archohall-kwin-compat /usr/local/bin/archohall-kwin-compat
pacman -Q > /opt/archohall-kwin-compat/build-packages.txt
printf '%s\n' 1b798c05c19b1124edb1e16623191fcd2c128fd0 > /opt/archohall-kwin-compat/upstream-commit.txt
cp -a /build/native-kwin/LICENSES /opt/archohall-kwin-compat/
cp /opt/native007/patch-kwin.py /opt/archohall-kwin-compat/
