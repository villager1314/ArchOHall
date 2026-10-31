#!/usr/bin/env python3
"""Fast source/recipe checks; does not claim Android or GPU execution."""
import ast
import importlib.util
from pathlib import Path
import subprocess
import tempfile

here = Path(__file__).resolve().parent
root = here.parents[1]
for path in [here / 'prepare-portal.py', here / 'prepare-runtime.py', root / 'diagnostics/arch-mobile-rootfs/normalize-runtime.py']:
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
