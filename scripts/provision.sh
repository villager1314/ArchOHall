#!/usr/bin/env bash
# Runs as root INSIDE an isolated build rootfs, never on the Android host.
set -euo pipefail
export LANG=C.UTF-8
pacman-key --init
pacman-key --populate archlinuxarm
# PRoot uses Android's kernel; do not upgrade board kernels or firmware in this userland.
remove_packages=()
for package in linux-aarch64 linux-firmware; do
    if pacman -Q "$package" >/dev/null 2>&1; then remove_packages+=("$package"); fi
done
if (( ${#remove_packages[@]} )); then
    pacman -Rns --noconfirm "${remove_packages[@]}"
fi
mapfile -t packages < <(sed -e '/^[[:space:]]*#/d' -e '/^[[:space:]]*$/d' /tmp/archohall-packages.txt)
pacman -Syu --noconfirm --needed "${packages[@]}"
sed -i 's/^#\(en_US.UTF-8 UTF-8\)/\1/; s/^#\(zh_CN.UTF-8 UTF-8\)/\1/' /etc/locale.gen
locale-gen
printf 'LANG=zh_CN.UTF-8\n' > /etc/locale.conf
printf 'archohall\n' > /etc/hostname
if id alarm >/dev/null 2>&1; then
    userdel -r alarm
fi
if ! id arch >/dev/null 2>&1; then
    useradd -m -u 1000 -s /bin/bash arch
fi
usermod -aG wheel arch
# No default passwords, SSH daemon, or passwordless sudo in the image.
passwd -l root
passwd -l arch
chmod 755 /usr/local/bin/archohall-mobile /usr/local/bin/archohall-session /usr/local/bin/archohall-init
rm -f /etc/machine-id
dbus-uuidgen --ensure=/etc/machine-id
kwin_wayland --help > /tmp/archohall-kwin-help.txt
grep -q -- '--x11-display' /tmp/archohall-kwin-help.txt
grep -q -- '--exit-with-session' /tmp/archohall-kwin-help.txt
test -f /usr/share/plasma/shells/org.kde.plasma.mobileshell/metadata.json
for executable in /usr/bin/kwin_wayland /usr/bin/plasmashell /usr/bin/konsole; do
    dependencies=$(ldd "$executable")
    if [[ $dependencies == *'not found'* ]]; then
        printf '%s\n' "$dependencies" >&2
        exit 1
    fi
done
pacman -Q > /root/archohall-packages.txt
# Keep systemd libraries: KDE depends on them even without booting systemd.
pacman -Scc --noconfirm
# Keep public trust records but never distribute the CI-generated local signing key.
gpgconf --homedir /etc/pacman.d/gnupg --kill all
rm -rf /etc/pacman.d/gnupg/private-keys-v1.d
rm -f /etc/machine-id /var/lib/dbus/machine-id /etc/ssh/ssh_host_* /tmp/archohall-kwin-help.txt
touch /etc/machine-id
find /var/log -type f -delete
find /root -maxdepth 1 -name '.*history' -delete
