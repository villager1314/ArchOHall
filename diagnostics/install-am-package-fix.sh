#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -euo pipefail
umask 077
case "${PREFIX:-}" in
    /data/data/com.archoh/files/usr|/data/user/0/com.archoh/files/usr) ;;
    *) echo '请在 ArchOHall 应用内的终端执行。' >&2; exit 1 ;;
esac
am_script="$PREFIX/bin/am"
am_dir="$PREFIX/libexec/termux-am"
[[ -f "$am_script" && -f "$am_dir/am.apk" ]] || { echo '未找到 TermuxAm。' >&2; exit 1; }
grep -Fq 'export CLASSPATH=' "$am_script" || { echo 'am 启动脚本与预期不同，未作修改。' >&2; exit 1; }
if ! grep -Eq 'com\.(termux\.termuxam\.Am|archoh\.compat\.TermuxAmLauncher)' "$am_script"; then
    echo 'am 启动脚本入口与预期不同，未作修改。' >&2; exit 1
fi
task_dir=$(mktemp -d "$PREFIX/tmp/archohall-am-fix.XXXXXX")
trap 'rm -rf "$task_dir"' EXIT
curl --fail --location --retry 2 --connect-timeout 20 --max-time 120 \
    'https://raw.githubusercontent.com/villager1314/ArchOHall/main/diagnostics/bin/archohall-am.zip' \
    -o "$task_dir/archohall-am.zip"
printf '%s  %s\n' 'cf00a569a1dbd62cb815a0aeb98a84f5d54e0115117e0a724995053ed1793a47' "$task_dir/archohall-am.zip" | sha256sum -c -
awk -v prefix="$PREFIX" -v helper="$am_dir/archohall-am.zip" '
    /^export PREFIX=/ {next}
    /^export CLASSPATH=/ {
        print "export PREFIX=\"" prefix "\""
        print "export CLASSPATH=\"$AM_APK_PATH:" helper "\""
        next
    }
    {gsub(/com\.termux\.termuxam\.Am/, "com.archoh.compat.TermuxAmLauncher"); print}
' "$am_script" > "$task_dir/am"
bash -n "$task_dir/am"
[[ -e "$am_script.before-archohall-caller-fix" ]] || cp -p "$am_script" "$am_script.before-archohall-caller-fix"
chmod 400 "$task_dir/archohall-am.zip" "$am_dir/am.apk"
mv "$task_dir/archohall-am.zip" "$am_dir/archohall-am.zip"
chmod 755 "$task_dir/am"
mv "$task_dir/am" "$am_script"
echo '已修正 TermuxAm 的安卓调用包名为 com.archoh。'
echo '现在重新执行：termux-setup-storage'
