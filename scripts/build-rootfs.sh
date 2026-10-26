#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 && $(uname -m) == aarch64 ]] || {
    echo 'Build requires root on an ARM64 Linux runner.' >&2; exit 1;
}
project=$(cd -- "$(dirname -- "$0")/.." && pwd)
work="$project/.build"
root="$work/rootfs"
out="$project/dist"
[[ ! -e $work && ! -e $out ]] || { echo 'Use a fresh checkout to build.' >&2; exit 1; }
mkdir -p "$root" "$out" "$work/gnupg"
chmod 700 "$work/gnupg"
# The os.archlinuxarm.org alias currently has a mismatched TLS certificate.
# Use the official California mirror while retaining TLS and GPG verification.
source_url=https://ca.us.mirror.archlinuxarm.org/os/ArchLinuxARM-aarch64-latest.tar.gz
fingerprint=68B3537F39A313B3E574D06777193F152BDBE6A6
download() { curl --fail --location --proto '=https' --proto-redir '=https' --retry 4 --connect-timeout 30 "$1" -o "$2"; }
download "$source_url" "$work/base.tar.gz"
download "$source_url.sig" "$work/base.tar.gz.sig"
download "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x$fingerprint" "$work/builder.asc"
actual=$(gpg --homedir "$work/gnupg" --batch --show-keys --with-colons "$work/builder.asc" | awk -F: '$1=="fpr" {print $10; exit}')
[[ $actual == "$fingerprint" ]] || { echo 'Unexpected upstream signing key.' >&2; exit 1; }
gpg --homedir "$work/gnupg" --batch --import "$work/builder.asc"
gpg --homedir "$work/gnupg" --batch --verify "$work/base.tar.gz.sig" "$work/base.tar.gz"
tar --numeric-owner --xattrs --acls -xpf "$work/base.tar.gz" -C "$root" --exclude='./dev/*' --exclude='dev/*'
cleanup() {
    # pacman-key starts GnuPG helpers that otherwise retain chroot resources.
    chroot "$root" /usr/bin/gpgconf --homedir /etc/pacman.d/gnupg --kill all || true
    for target in "$root/proc" "$root/dev" "$root"; do
        if mountpoint -q "$target"; then umount -R "$target"; fi
    done
}
trap cleanup EXIT
mount --bind "$root" "$root"
mkdir -p "$root/dev" "$root/proc" "$root/sys" "$root/tmp"
chmod 1777 "$root/tmp"
mount --rbind /dev "$root/dev"
mount --make-rslave "$root/dev"
mount -t proc proc "$root/proc"
# Replace a possible systemd-resolved symlink without writing through it.
rm -f "$root/etc/resolv.conf"
cp -L /etc/resolv.conf "$root/etc/resolv.conf"
# HTTPS only; do not disable pacman's package signature checking.
# shellcheck disable=SC2016 # pacman expands these variables, not this shell.
printf 'Server = https://ca.us.mirror.archlinuxarm.org/$arch/$repo\n' > "$root/etc/pacman.d/mirrorlist"
# Do not copy the checkout user's ownership onto / or /usr in the image.
cp -a --no-preserve=ownership "$project/rootfs/." "$root/"
install -m 644 "$project/packages.txt" "$root/tmp/archohall-packages.txt"
install -m 755 "$project/scripts/provision.sh" "$root/tmp/archohall-provision.sh"
# Qt tools used for validation must not try to connect to the runner display.
chroot "$root" /usr/bin/env QT_QPA_PLATFORM=offscreen /bin/bash /tmp/archohall-provision.sh
cp "$root/root/archohall-packages.txt" "$out/packages.txt"
rm -f "$root/root/archohall-packages.txt" "$root/tmp/archohall-packages.txt" "$root/tmp/archohall-provision.sh"
cleanup
trap - EXIT
# Resolver is supplied by the runtime after import; don't ship CI-local DNS.
printf 'nameserver 1.1.1.1\nnameserver 8.8.8.8\n' > "$root/etc/resolv.conf"
{
    printf 'project=ArchOHall\narchitecture=aarch64\nbuilt_at=%s\n' "$(date -u +%FT%TZ)"
    printf 'commit=%s\nsource=%s\n' "${GITHUB_SHA:-local}" "$source_url"
    printf 'source_sha256=%s\n' "$(sha256sum "$work/base.tar.gz" | cut -d ' ' -f1)"
    printf 'source_signer=%s\nvalidation=packages-and-linker-only; Android runtime not tested\n' "$fingerprint"
} > "$out/build-info.txt"
tar --numeric-owner --one-file-system -C "$root" \
    --exclude='./dev/*' --exclude='./proc/*' --exclude='./sys/*' \
    --exclude='./run/*' --exclude='./tmp/*' \
    -cpf - . | xz -T2 -6 > "$out/archohall-aarch64.tar.xz"
xz -t "$out/archohall-aarch64.tar.xz"
tar -tJf "$out/archohall-aarch64.tar.xz" > "$work/archive-contents.txt"
grep -qx './usr/local/bin/archohall-mobile' "$work/archive-contents.txt"
install -m 644 "$project/scripts/start-termux.sh" "$out/start-termux.sh"
if (( $(stat -c %s "$out/archohall-aarch64.tar.xz") >= 2147483648 )); then
    split -b 1024M -d -a 3 "$out/archohall-aarch64.tar.xz" "$out/archohall-aarch64.tar.xz.part"
    rm "$out/archohall-aarch64.tar.xz"
fi
(cd "$out"; find . -maxdepth 1 -type f -print0 | sort -z | xargs -0 sha256sum > "$work/SHA256SUMS")
mv "$work/SHA256SUMS" "$out/SHA256SUMS"
echo 'Rootfs packaging completed. Android desktop startup still requires device testing.'
