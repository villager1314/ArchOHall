#!/usr/bin/env python3
"""Validate an untested compiled candidate before reusing it for runtime tests."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile


def verify(root, candidate, project):
    metadata = json.loads((candidate/'native-component.json').read_text())
    if metadata.get('version') != '0.07' or metadata.get('kwinSource') != '1b798c05c19b1124edb1e16623191fcd2c128fd0':
        raise ValueError('Candidate is not the pinned 0.07 compositor')
    for name in ('patch-kwin.py', 'build-in-arch.sh', 'archohall-kwin-compat'):
        actual = hashlib.sha256((project/'diagnostics/native007'/name).read_bytes()).hexdigest()
        if metadata.get('buildInputs', {}).get(name) != actual:
            raise ValueError('Candidate build inputs changed: ' + name)
    expected_names = {'kwin', 'plasma-mobile', 'qt6-base', 'qt6-declarative', 'qt6-wayland', 'kglobalacceld'}
    if set(metadata['packages']) != expected_names:
        raise ValueError('Incomplete candidate package manifest')
    for name, expected in metadata['packages'].items():
        actual = subprocess.check_output(['chroot', str(root), 'pacman', '-Q', name], text=True).split()[1]
        if actual != expected:
            raise ValueError(f'Candidate dependency changed: {name} {actual}; expected {expected}')
    archive = candidate/'archohall-native-007-aarch64.tar.xz'
    with archive.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != metadata['sha256']:
        raise ValueError('Candidate archive checksum mismatch')
    with tarfile.open(archive) as bundle:
        for member in bundle:
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or not (
                member.name == 'usr/local/bin/archohall-kwin-compat'
                or member.name == 'opt/archohall-kwin-compat'
                or member.name.startswith('opt/archohall-kwin-compat/')
            ):
                raise ValueError('Unexpected candidate archive path: ' + member.name)
    if not (candidate/'kwin-native-upstream-source.tar.gz').is_file():
        raise ValueError('Candidate source archive missing')
    print('PASS: candidate checksum, pinned build inputs, archive scope and exact package versions')


if __name__ == '__main__':
    verify(Path(sys.argv[1]), Path(sys.argv[2]), Path(__file__).resolve().parents[1])
