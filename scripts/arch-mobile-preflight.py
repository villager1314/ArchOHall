#!/usr/bin/env python3
"""Read-only checks of an unpacked Arch Mobile image; not an installer."""
import argparse
import json
from pathlib import Path


def inspect(root):
    root = root.resolve()
    problems = []
    release = root / 'etc/os-release'
    identity = release.read_text() if release.is_file() else ''
    if not any(line.strip().strip('"') in ('ID=arch', 'ID=archarm')
               for line in identity.splitlines()):
        problems.append('Expected Arch Linux ARM os-release identity')
    for program in ('pacman', 'kwin_wayland', 'plasmashell', 'dbus-run-session'):
        if not (root / 'usr/bin' / program).is_file():
            problems.append('Missing usr/bin/' + program)
    packages = {}
    for desc in (root / 'var/lib/pacman/local').glob('*/desc'):
        lines = desc.read_text().splitlines()
        fields = {line: lines[i + 1] for i, line in enumerate(lines[:-1])
                  if line in ('%NAME%', '%VERSION%', '%ARCH%')}
        name = fields.get('%NAME%')
        if name in ('kwin', 'plasma-mobile', 'plasma-workspace',
                    'qt6-base', 'qt6-declarative', 'qt6-wayland'):
            packages[name] = fields.get('%VERSION%', '')
            if fields.get('%ARCH%') not in ('aarch64', 'any'):
                problems.append('Unexpected architecture for ' + name)
    for package in ('kwin', 'plasma-mobile', 'plasma-workspace',
                    'qt6-base', 'qt6-declarative', 'qt6-wayland'):
        if package not in packages:
            problems.append('Missing package metadata: ' + package)
    return {'packages': packages, 'problems': problems,
            'image_preflight_pass': not problems,
            'anland_backend_verified': False,
            'device_rendering_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rootfs', type=Path)
    result = inspect(parser.parse_args().rootfs)
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result['problems']))
