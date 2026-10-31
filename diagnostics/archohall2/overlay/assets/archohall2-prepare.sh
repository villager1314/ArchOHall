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
stage=sudo-ownership
# Ownership is recorded by the guest engine, not a host chown of app data.
for file in /usr/bin/sudo /etc/sudo.conf /etc/sudoers /etc/sudoers.d; do
    if [[ -e $file ]]; then chown 0:0 "$file"; fi
done
if [[ -d /etc/sudoers.d ]]; then find /etc/sudoers.d -maxdepth 1 -type f -exec chown 0:0 {} +; fi
if [[ -d /usr/lib/sudo ]]; then chown -R 0:0 /usr/lib/sudo; fi
if [[ -x /usr/bin/sudo ]]; then chmod 4755 /usr/bin/sudo; fi
if command -v visudo >/dev/null; then visudo -c; fi
stage=xwayland-abi
candidate=/usr/local/lib/portal-xwayland-default/Xwayland
variant=stock
if [[ -x $candidate ]]; then
    dependencies=$(ldd "$candidate" 2>&1) || dependencies='not found: loader failed'
    if ! grep -q 'not found' <<< "$dependencies" && "$candidate" -version >/dev/null 2>&1; then
        variant=portal
    else
        printf 'stage=sudo-ownership
# Ownership is recorded by the guest engine, not a host chown of app data.
for file in /usr/bin/sudo /etc/sudo.conf /etc/sudoers /etc/sudoers.d; do
    if [[ -e $file ]]; then chown 0:0 "$file"; fi
done
if [[ -d /etc/sudoers.d ]]; then find /etc/sudoers.d -maxdepth 1 -type f -exec chown 0:0 {} +; fi
if [[ -d /usr/lib/sudo ]]; then chown -R 0:0 /usr/lib/sudo; fi
if [[ -x /usr/bin/sudo ]]; then chmod 4755 /usr/bin/sudo; fi
if command -v visudo >/dev/null; then visudo -c; fi
stage=xwayland-abi variant=stock reason=dependency-or-execution-check-failed\n%s\n' "$dependencies" >&2
    fi
fi
printf '%s\n' "$variant" > /etc/archohall2/xwayland-variant
stage=machine-id
dbus-uuidgen --ensure=/etc/machine-id
printf 'stage=arch-login-preparation status=passed\n'
