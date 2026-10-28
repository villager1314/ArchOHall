#!/usr/bin/env bash
# Run before submitting an ARM64 integration build. No publishing or network writes.
set -euo pipefail
project=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project"
shellcheck=${SHELLCHECK:-shellcheck}
command -v "$shellcheck" >/dev/null
python3 - <<'PY'
import ast
from pathlib import Path
for directory in ('android', 'scripts', 'tests', 'diagnostics/native007'):
    for source in Path(directory).rglob('*.py'):
        ast.parse(source.read_text(), filename=str(source))
print('PASS: Python source syntax')
PY
mapfile -t scripts < <(find scripts diagnostics/native007 -type f \( -name '*.sh' -o -name archohall-kwin-compat \) | sort)
scripts+=(android/desktop-compat-install.sh android/host-bridge/host-audio.sh
 rootfs/usr/local/bin/archohall-mobile rootfs/usr/local/bin/archohall-session
 rootfs/usr/local/bin/archohall-install-tiles rootfs/usr/local/bin/archohall-controls
 rootfs/usr/local/bin/archohall-restore-desktop-support)
for script in "${scripts[@]}"; do bash -n "$script"; done
"$shellcheck" -s bash "${scripts[@]}"
echo 'PASS: Bash syntax and ShellCheck'
python3 -m unittest discover -s tests -v
LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe LP_NUM_THREADS=2 python3 tests/probe_software_egl.py
if [[ $# == 1 ]]; then
    # Extract pristine files with git show; never reset the developer's checkout.
    python3 - "$1" "$project" <<'PY'
from pathlib import Path
import subprocess, sys, tempfile
upstream, project = map(Path, sys.argv[1:])
commit = '1b798c05c19b1124edb1e16623191fcd2c128fd0'
files = ['src/core/gpumanager.cpp', 'src/backends/x11/x11_windowed_backend.cpp',
         'src/backends/x11/x11_windowed_egl_backend.cpp',
         'src/backends/x11/x11_windowed_egl_backend.h']
with tempfile.TemporaryDirectory(prefix='archohall-patch-') as directory:
    root = Path(directory)
    for name in files:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output(['git', '-C', str(upstream), 'show', commit + ':' + name]))
    subprocess.run([sys.executable, str(project/'diagnostics/native007/patch-kwin.py'), str(root)], check=True)
print('PASS: native patch applies to pristine pinned KWin source')
PY
elif [[ $# != 0 ]]; then
    echo "Usage: $0 [local-kwin-git-checkout]" >&2; exit 2
else
    echo 'SKIP: patch applicability (supply the pinned KWin git checkout)'
fi
echo 'Local checks complete. KWin/Wayland integration and Android device tests remain separate requirements.'
