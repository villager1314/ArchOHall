#!/usr/bin/env bash
set -euo pipefail
stage=identity
trap 'status=$?; printf "stage=%s status=failed exit=%s line=%s\n" "$stage" "$status" "$LINENO" >&2; exit "$status"' ERR
uid=$(id -u arch)
gid=$(id -g arch)
[[ $uid =~ ^[0-9]+$ && $gid =~ ^[0-9]+$ ]]
[[ $uid -gt 0 && $gid -gt 0 ]]
printf 'stage=identity user=arch uid=%s gid=%s\n' "$uid" "$gid"
# Used by the local account-contract regression check; no filesystem writes.
if [[ ${1:-} == --identity-only ]]; then exit 0; fi
stage=account-permissions
chmod 0644 /etc/passwd /etc/group
stage=runtime-directories
install -d -m 0700 -o "$uid" -g "$gid" "/run/user/$uid" /var/lib/localdesktop/session
stage=home-ownership
if [[ ! -f /home/arch/.archohall2-owned ]]; then
    chown -R "$uid:$gid" /home/arch
    touch /home/arch/.archohall2-owned
    chown "$uid:$gid" /home/arch/.archohall2-owned
fi
stage=machine-id
dbus-uuidgen --ensure=/etc/machine-id
printf 'stage=arch-login-preparation status=passed\n'
