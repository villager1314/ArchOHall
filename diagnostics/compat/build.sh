#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 && $(uname -m) == aarch64 ]]
project=$(cd -- "$(dirname -- "$0")/../.." && pwd)
work="$project/.kwin-compat-build"
root="$work/root"
out="$project/dist/kwin-compat"
mkdir -p "$root" "$work/gnupg" "$out"
chmod 700 "$work/gnupg"
download() { curl --fail --location --proto '=https' --proto-redir '=https' --retry 4 --connect-timeout 30 "$1" -o "$2"; }
source_url=https://ca.us.mirror.archlinuxarm.org/os/ArchLinuxARM-aarch64-latest.tar.gz
fingerprint=68B3537F39A313B3E574D06777193F152BDBE6A6
download "$source_url" "$work/base.tar.gz"
download "$source_url.sig" "$work/base.tar.gz.sig"
download "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x$fingerprint" "$work/builder.asc"
actual=$(gpg --homedir "$work/gnupg" --batch --show-keys --with-colons "$work/builder.asc" | awk -F: '$1=="fpr" {print $10; exit}')
[[ $actual == "$fingerprint" ]]
gpg --homedir "$work/gnupg" --batch --import "$work/builder.asc"
gpg --homedir "$work/gnupg" --batch --verify "$work/base.tar.gz.sig" "$work/base.tar.gz"
tar --numeric-owner -xpf "$work/base.tar.gz" -C "$root" --exclude='./dev/*' --exclude='dev/*'
cleanup() {
    chroot "$root" /usr/bin/gpgconf --homedir /etc/pacman.d/gnupg --kill all || true
    for target in "$root/proc" "$root/dev"; do
        if mountpoint -q "$target"; then umount -R "$target"; fi
    done
}
trap cleanup EXIT
mount --rbind /dev "$root/dev"
mount --make-rslave "$root/dev"
mount -t proc proc "$root/proc"
rm -f "$root/etc/resolv.conf"
cp -L /etc/resolv.conf "$root/etc/resolv.conf"
printf 'Server = https://ca.us.mirror.archlinuxarm.org/$arch/$repo\n' > "$root/etc/pacman.d/mirrorlist"
mkdir -p "$root/opt/compat-build"
cp -a "$project/diagnostics/compat/." "$root/opt/compat-build/"
chroot "$root" /bin/bash /opt/compat-build/build-in-arch.sh
cp -a "$root/compat-results/." "$out/"
cp "$root/opt/archohall-kwin-compat/build-packages.txt" "$out/"
cp "$root/tmp/kwin-source.tar.gz" "$out/kwin-upstream-source.tar.gz"
cp -a "$project/diagnostics/compat" "$out/build-scripts"
tar -C "$root" -cJf "$out/archohall-kwin-compat-6.7.5-aarch64.tar.xz" \
    opt/archohall-kwin-compat usr/local/bin/archohall-kwin-compat
cp "$work/base.tar.gz.sig" "$out/base-signature.sig"
printf '%s\n' 'Experimental KWin 6.7.5 with X11 QPainter and null-udev fix. CI Xvfb test only; Android not yet tested.' > "$out/README.txt"
(cd "$out" && sha256sum *.tar.xz > SHA256SUMS)
