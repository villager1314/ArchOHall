#!/usr/bin/env bash
set -euo pipefail
root="$ARCHOHALL_ROOTFS"
work="$ARCHOHALL_COMPAT_WORK"
[[ -f "$root/usr/bin/kwin_wayland" ]] || { echo '请先导入 ArchOHall 容器'; exit 1; }
for package in qt6-base qt6-declarative qt6-wayland; do
    case "$package" in qt6-base) expected=6.12.0-3;; qt6-declarative) expected=6.12.0-2;; qt6-wayland) expected=6.12.0-1;; esac
    actual=$(awk '/^%VERSION%$/ {getline; print; exit}' "$root/var/lib/pacman/local/$package-"*/desc)
    [[ "$actual" == "$expected" ]] || { echo "Qt 版本不匹配：$package 当前 $actual，需要 $expected；未修改容器"; exit 1; }
done
mkdir -p "$root/opt"
stage=$(mktemp -d "$root/opt/.archohall-compat-004.XXXXXX")
trap 'rm -rf "$stage"' EXIT
echo '展开已校验的软件兼容组件'
tar --no-same-owner -xJf "$work/desktop-compat.tar.xz" -C "$stage"
test -x "$stage/opt/archohall-kwin-compat/bin/kwin_wayland"
bash -n "$work/mobile"
bash -n "$work/session"
echo '保留原来的桌面启动脚本'
for name in archohall-mobile archohall-session; do
    f="$root/usr/local/bin/$name"
    [[ -e "$f.before-004-compat" ]] || cp -p "$f" "$f.before-004-compat"
done
if [[ -e "$root/opt/archohall-kwin-compat" ]]; then
    mv "$root/opt/archohall-kwin-compat" "$root/opt/archohall-kwin-compat.backup-$(date +%s)-$$"
fi
mv "$stage/opt/archohall-kwin-compat" "$root/opt/archohall-kwin-compat"
install -m 755 "$stage/usr/local/bin/archohall-kwin-compat" "$root/usr/local/bin/archohall-kwin-compat"
install -m 755 "$work/mobile" "$root/usr/local/bin/archohall-mobile.004-new"
install -m 755 "$work/session" "$root/usr/local/bin/archohall-session.004-new"
mv "$root/usr/local/bin/archohall-mobile.004-new" "$root/usr/local/bin/archohall-mobile"
mv "$root/usr/local/bin/archohall-session.004-new" "$root/usr/local/bin/archohall-session"
printf '%s\n' '6.7.5-QPainter-004' > "$root/.archohall-compat-004"
echo '软件兼容组件安装完成，可以启动 Plasma Mobile'
