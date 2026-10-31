#!/usr/bin/env python3
"""Fast source/recipe checks; does not claim Android or GPU execution."""
import ast
import importlib.util
from pathlib import Path
import subprocess
import tempfile

here = Path(__file__).resolve().parent
root = here.parents[1]
for path in [here / 'prepare-portal.py', here / 'prepare-runtime.py', here / 'reuse-upstream.py', here / 'verify-prepared-profile.py', root / 'diagnostics/arch-mobile-rootfs/normalize-runtime.py']:
    ast.parse(path.read_text(), filename=str(path))
for path in (here / 'overlay/assets').glob('*.sh'):
    subprocess.run(['bash', '-n', str(path)], check=True)
spec = importlib.util.spec_from_file_location('normalize_runtime', root / 'diagnostics/arch-mobile-rootfs/normalize-runtime.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as d:
    tree = Path(d)
    (tree/'etc').mkdir()
    (tree/'etc/arch-release').touch()
    (tree/'sys').mkdir(mode=0o555)
    (tree/'var').mkdir()
    (tree/'var/run').symlink_to('/run')
    assert module.normalize(tree) == 1
    assert (tree/'var/run').readlink() == Path('../run')
    assert (tree/'sys').stat().st_mode & 0o777 == 0o755
    assert module.normalize(tree) == 0
print('Profile syntax, shell parsing, future rootfs normalization: PASS')
# Arch ARM images may already reserve UID 1000 for another account. Exercise the
# actual guest preparation script with both valid IDs, without touching host files.
import os
with tempfile.TemporaryDirectory() as d:
    mock = Path(d)/'id'
    mock.write_text('#!/bin/sh\ncase "$1" in -u) echo "$TEST_UID";; -g) echo "$TEST_GID";; *) exit 2;; esac\n')
    mock.chmod(0o755)
    script = here/'overlay/assets/archohall2-prepare.sh'
    for uid, gid, expected in [('1000','1000', True), ('1001','1001', True), ('0','0', False)]:
        result = subprocess.run(['bash', str(script), '--identity-only'], env={**os.environ, 'PATH': d+os.pathsep+os.environ['PATH'], 'TEST_UID':uid, 'TEST_GID':gid}, capture_output=True, text=True)
        assert (result.returncode == 0) == expected, result.stderr
        if expected:
            assert f'uid={uid} gid={gid}' in result.stdout
        else:
            assert 'stage=identity status=failed' in result.stderr
print('Guest account IDs 1000/1001 and root rejection: PASS')
