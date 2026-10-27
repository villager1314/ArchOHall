#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Apply only to the existing diagnostic runner; no APK or rootfs replacement.
set -euo pipefail
umask 077
case "${PREFIX:-}" in
    /data/data/com.archoh/files/usr|/data/user/0/com.archoh/files/usr) ;;
    *) echo '请在 ArchOHall 应用内的终端执行。' >&2; exit 1 ;;
esac
[[ "$(uname -m)" == aarch64 ]] || { echo '此补丁仅支持 ARM64。' >&2; exit 1; }
runner="$PREFIX/../containers/archohall/usr/local/bin/archohall-debug-runner"
backup="$runner.before-udev-guard"
old_preload='LD_PRELOAD=/tmp/libarchohall-crashtrace.so'
new_preload='LD_PRELOAD=/tmp/libarchohall-udev-guard.so:/tmp/libarchohall-crashtrace.so'
[[ -f "$runner" && -f "$PREFIX/tmp/libarchohall-crashtrace.so" ]] || {
    echo '未找到之前的调试脚本或崩溃跟踪库，未作修改。' >&2; exit 1;
}
if ! grep -Fq "$old_preload" "$runner" && ! grep -Fq "$new_preload" "$runner"; then
    echo '调试脚本内容与预期不同，未作修改。' >&2; exit 1
fi
task_dir="$(mktemp -d "$PREFIX/tmp/archohall-udev-guard.XXXXXX")"
trap 'rm -rf "$task_dir"' EXIT
base_url='https://raw.githubusercontent.com/villager1314/ArchOHall/main/diagnostics/bin/aarch64'
curl --fail --location --retry 2 --connect-timeout 20 --max-time 180 \
    "$base_url/libarchohall-udev-guard.so.gz" -o "$task_dir/guard.so.gz"
gzip -dc "$task_dir/guard.so.gz" > "$task_dir/libarchohall-udev-guard.so"
printf '%s  %s\n' '604ca8dd96aa4e9cab3e0939ad0772da683f1ccd89329bcd8d4bfe8661c5e7d2' \
    "$task_dir/libarchohall-udev-guard.so" | sha256sum -c -
sed "s|$old_preload|$new_preload|g" "$runner" > "$task_dir/runner"
# Avoid adding the guard twice when reinstalling.
if grep -Fq "$new_preload" "$runner"; then cp "$runner" "$task_dir/runner"; fi
bash -n "$task_dir/runner"
if [[ ! -e "$backup" ]]; then cp -p "$runner" "$backup"; fi
chmod 644 "$task_dir/libarchohall-udev-guard.so"
mv "$task_dir/libarchohall-udev-guard.so" "$PREFIX/tmp/libarchohall-udev-guard.so"
chmod 755 "$task_dir/runner"
mv "$task_dir/runner" "$runner"
echo '已安装 udev 空指针临时补丁，原脚本已备份。'
echo '补丁只在容器内的 kwin_wayland 进程加载。'
echo '现在执行：bash ~/.archohall/launch.sh'
