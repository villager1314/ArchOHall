#!/usr/bin/env python3
"""Normalize a future, unmounted build tree, never a user's installed rootfs."""
import argparse
import os
from pathlib import Path
import posixpath
import stat


def normalize(root):
    root = root.resolve()
    if not (root / 'etc/arch-release').is_file():
        raise ValueError('Expected an Arch build tree')
    if root == Path('/'):
        raise ValueError('Run on an unmounted build tree, never the host root')
    for name in ('proc', 'sys', 'run', 'dev', 'etc', 'opt'):
        path = root / name
        if path.is_symlink():
            raise ValueError(f'Expected real directory: {name}')
        path.mkdir(exist_ok=True)
        path.chmod(0o755)
    tmp = root / 'tmp'
    if tmp.is_symlink():
        raise ValueError('tmp is a symlink')
    tmp.mkdir(exist_ok=True)
    tmp.chmod(0o1777)
    changed = 0
    # os.walk does not descend into directory links. Every absolute guest link
    # is translated lexically, without reading any host-side target.
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
            path = Path(parent) / name
            if not stat.S_ISLNK(path.lstat().st_mode):
                continue
            target = os.readlink(path)
            if target.startswith('/'):
                relative = posixpath.relpath(posixpath.normpath(target).lstrip('/') or '.', path.parent.relative_to(root).as_posix())
                path.unlink()
                path.symlink_to(relative)
                changed += 1
    return changed


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    args = p.parse_args()
    print(f'Normalized absolute guest links: {normalize(args.root)}')
