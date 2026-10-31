import json
import subprocess
expected = json.load(open('/input/package-candidate.json'))['packages']
for name in ('kwin', 'plasma-mobile', 'plasma-workspace', 'qt6-base', 'qt6-declarative', 'qt6-wayland'):
    installed = subprocess.check_output(['pacman', '-Q', name], text=True).split()[1]
    if installed != expected[name]['version']:
        raise SystemExit(f'Refusing ABI drift: {name}: {installed}; expected {expected[name]["version"]}')
