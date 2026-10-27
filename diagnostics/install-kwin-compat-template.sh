#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail
umask 077
case "${PREFIX:-}" in
    /data/data/com.archoh/files/usr|/data/user/0/com.archoh/files/usr) ;;
    *) echo '请在 ArchOHall 应用内的终端执行。' >&2; exit 1 ;;
esac
[[ "$(uname -m)" == aarch64 ]]
root="$PREFIX/../containers/archohall"
runner="$root/usr/local/bin/archohall-debug-runner"
session="$root/usr/local/bin/archohall-session"
[[ -f "$runner" && -f "$session" && -f "$PREFIX/tmp/libarchohall-crashtrace.so" ]] || {
    echo '未找到之前的调试环境，未作修改。' >&2; exit 1;
}
if ! grep -Fq ' kwin_wayland ' "$runner" && ! grep -Fq ' /usr/local/bin/archohall-kwin-compat ' "$runner"; then
    echo '调试脚本与预期不同，未作修改。' >&2; exit 1
fi
check_qt() {
    local package="$1" expected="$2" actual
    actual=$(awk '/^%VERSION%$/ {getline; print; exit}' "$root/var/lib/pacman/local/$package-"*/desc)
    [[ "$actual" == "$expected" ]] || {
        printf '依赖版本不匹配：%s 手机=%s 编译环境=%s；未作修改。\n' "$package" "$actual" "$expected" >&2
        exit 1
    }
}
check_qt qt6-base '@QT_BASE@'
check_qt qt6-declarative '@QT_DECLARATIVE@'
check_qt qt6-wayland '@QT_WAYLAND@'
mkdir -p "$root/opt"
task_dir=$(mktemp -d "$root/opt/.archohall-compat-install.XXXXXX")
trap 'rm -rf "$task_dir"' EXIT
url='https://github.com/villager1314/ArchOHall/releases/download/@RELEASE_TAG@/archohall-kwin-compat-6.7.5-aarch64.tar.xz'
curl --fail --location --retry 3 --connect-timeout 20 --max-time 600 "$url" -o "$task_dir/compat.tar.xz"
printf '%s  %s\n' '@PACKAGE_SHA256@' "$task_dir/compat.tar.xz" | sha256sum -c -
tar -xJf "$task_dir/compat.tar.xz" -C "$task_dir"
test -x "$task_dir/opt/archohall-kwin-compat/bin/kwin_wayland"
sed -e 's| kwin_wayland | /usr/local/bin/archohall-kwin-compat |g' \
    -e 's|LD_PRELOAD=/tmp/libarchohall-udev-guard.so:/tmp/libarchohall-crashtrace.so|LD_PRELOAD=/tmp/libarchohall-crashtrace.so|g' \
    "$runner" > "$task_dir/runner"
if grep -q '^export QT_QUICK_BACKEND=software$' "$session"; then
    cp "$session" "$task_dir/session"
else
    sed '2i export QT_QUICK_BACKEND=software' "$session" > "$task_dir/session"
fi
bash -n "$task_dir/runner"
bash -n "$task_dir/session"
[[ -e "$runner.before-kwin-compat" ]] || cp -p "$runner" "$runner.before-kwin-compat"
[[ -e "$session.before-kwin-compat" ]] || cp -p "$session" "$session.before-kwin-compat"
if [[ -e "$root/opt/archohall-kwin-compat" ]]; then
    mv "$root/opt/archohall-kwin-compat" "$root/opt/archohall-kwin-compat.backup-$(date +%s)"
fi
mv "$task_dir/opt/archohall-kwin-compat" "$root/opt/archohall-kwin-compat"
install -m 755 "$task_dir/usr/local/bin/archohall-kwin-compat" "$root/usr/local/bin/archohall-kwin-compat"
chmod 755 "$task_dir/runner" "$task_dir/session"
mv "$task_dir/runner" "$runner"
mv "$task_dir/session" "$session"
printf '%s\n' '兼容版已独立安装，原调试脚本已备份。' \
    '先执行：rm -f "$PREFIX/tmp/.X11-unix/X0" "$PREFIX/tmp/.X0-lock" ~/.archohall/stop-requested' \
    '然后执行：bash ~/.archohall/launch.sh'
