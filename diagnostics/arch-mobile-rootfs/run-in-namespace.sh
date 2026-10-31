#!/usr/bin/env bash
# Run only inside a private mount + PID namespace created by unshare.
set -euo pipefail
root=$(realpath "$1")
input=$(realpath "$2")
output=$(realpath "$3")
cache=$(realpath "$4")
phase=$5
case "$phase" in
    dependencies) guest_script=install-dependencies.sh ;;
    overlay) guest_script=install-guest.sh ;;
    *) echo 'Unknown guest build phase' >&2; exit 2 ;;
esac
# This changes propagation only inside our new mount namespace.
mount --make-rprivate /
log_mounts() {
    result=$?
    trap - EXIT
    cat /proc/self/mountinfo > "$output/mountinfo-$phase-exit.txt" || true
    exit "$result"
}
trap log_mounts EXIT
mkdir -p "$root/input" "$root/output" "$root/proc" "$root/dev" "$root/var/cache/pacman/pkg"
mount --bind "$root" "$root"
mount --bind "$input" "$root/input"
mount --bind "$output" "$root/output"
mount --bind "$cache" "$root/var/cache/pacman/pkg"
mount -t proc proc "$root/proc"
mount --rbind /dev "$root/dev"
mount --make-rprivate "$root/dev"
ln -sfn /proc/self/mounts "$root/etc/mtab"
cat /proc/self/mountinfo > "$output/mountinfo-$phase-enter.txt"
chroot "$root" /bin/bash "/input/$guest_script"
# No mounts escape this namespace. PID namespace exit also ends guest children.
