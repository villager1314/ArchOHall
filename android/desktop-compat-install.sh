#!/usr/bin/env bash
set -euo pipefail
root="$ARCHOHALL_ROOTFS"
work="$ARCHOHALL_COMPAT_WORK"
[[ -f "$root/usr/bin/kwin_wayland" ]] || { echo '请先导入 ArchOHall 容器'; exit 1; }
# Inspect guest package metadata read-only before replacing compositor files.
env -u LD_PRELOAD "$PREFIX/bin/proot" --link2symlink -0 -r "$root" -b /dev -b /proc -b "$work:/run/archohall-native-install" -w /root \
 /usr/bin/env -i HOME=/root PATH=/usr/bin:/bin /usr/bin/python3 - / /run/archohall-native-install/native-component.json <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);meta=json.loads(Path(sys.argv[2]).read_text())
assert meta['version']=='0.07'
for package,expected in meta['packages'].items():
 records=list((root/'var/lib/pacman/local').glob(package+'-*/desc'))
 matches=[]
 for record in records:
  text=record.read_text().splitlines()
  fields={text[i]:text[i+1] for i in range(len(text)-1) if text[i].startswith('%')}
  if fields.get('%NAME%')==package:matches.append(fields.get('%VERSION%'))
 if matches != [expected]:
  raise SystemExit(f'组件版本不匹配：{package} 当前 {matches}，需要 {expected}。请使用 0.07 Release 配套 rootfs；原容器未修改。')
PY
mkdir -p "$root/opt"
stage=$(mktemp -d "$root/opt/.archohall-native-007.XXXXXX")
trap 'rm -rf "$stage"' EXIT
tar --no-same-owner -xJf "$work/desktop-compat.tar.xz" -C "$stage"
test -x "$stage/opt/archohall-kwin-compat/bin/kwin_wayland"
for name in mobile session; do bash -n "$work/$name"; done
for name in archohall-mobile archohall-session archohall-kwin-compat; do
 f="$root/usr/local/bin/$name"
 [[ ! -e "$f" || -e "$f.before-007-native" ]] || cp -p "$f" "$f.before-007-native"
done
if [[ -e "$root/opt/archohall-kwin-compat" ]]; then
 mv "$root/opt/archohall-kwin-compat" "$root/opt/archohall-kwin-compat.before-native-007-$(date +%s)-$$"
fi
mv "$stage/opt/archohall-kwin-compat" "$root/opt/archohall-kwin-compat"
install -m 644 "$work/native-component.json" "$root/opt/archohall-kwin-compat/native-component.json"
install -m 755 "$stage/usr/local/bin/archohall-kwin-compat" "$root/usr/local/bin/archohall-kwin-compat"
install -m 755 "$work/mobile" "$root/usr/local/bin/archohall-mobile"
install -m 755 "$work/session" "$root/usr/local/bin/archohall-session"
printf '0.07\n' > "$root/.archohall-native-007"
echo '原生 OpenGL 多任务组件已安装，版本检查通过；旧组件保留为备份'
