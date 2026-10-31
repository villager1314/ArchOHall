#!/usr/bin/env bash
set -euo pipefail
[[ $(uname -m) == aarch64 ]]
pacman-key --init
pacman-key --populate archlinuxarm
remove=()
for p in linux-aarch64 linux-firmware; do
    if pacman -Q "$p" >/dev/null 2>&1; then remove+=("$p"); fi
done
if ((${#remove[@]})); then pacman -Rns --noconfirm "${remove[@]}"; fi
pacman -Syu --needed --noconfirm --disable-sandbox \
    kwin plasma-mobile plasma-workspace plasma-keyboard plasma-settings \
    konsole dolphin dbus python sudo xorg-xwayland mesa qt6-wayland noto-fonts noto-fonts-cjk
python /input/verify-packages.py
# Install the already compiled compositor; never compile KWin in this job.
tar -xJf /input/kwin-6.8.2-anland-arm64-experimental.tar.xz -C /
printf '%s\n' '/opt/archohall-mobile/lib' > /etc/ld.so.conf.d/archohall-mobile.conf
ldconfig
ldd /opt/archohall-mobile/bin/kwin_wayland | tee /output/kwin-ldd.txt
if grep -q 'not found' /output/kwin-ldd.txt; then exit 1; fi
QT_QPA_PLATFORM=offscreen /opt/archohall-mobile/bin/kwin_wayland --help > /output/kwin-help.txt
grep -q -- '--anland' /output/kwin-help.txt
install -Dm755 /input/arch-mobile-session.sh /usr/local/bin/start-archohall-mobile
useradd -m -s /bin/bash arch
passwd -l root
passwd -l arch
pacman -Q > /output/rootfs-packages.txt
mkdir -p /usr/share/archohall
cp /input/provenance.json /usr/share/archohall/build-provenance.json
# This is a component image, not a validated Android runtime yet.
printf '%s\n' 'Experimental Arch Mobile image; Android GPU/host integration pending.' > /usr/share/archohall/EXPERIMENTAL
