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
pacman -Q > /output/base-packages.txt
