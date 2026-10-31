#!/usr/bin/env python3
"""Exercise native XKB with a guest absolute link, then its relative repair.
Linux-host regression only: this is not an Android packaged-library test.
"""
import ctypes
import ctypes.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def probe(path):
    os.environ['XKB_CONFIG_ROOT'] = path
    library = ctypes.CDLL(ctypes.util.find_library('xkbcommon'))
    library.xkb_context_new.argtypes = [ctypes.c_int]
    library.xkb_context_new.restype = ctypes.c_void_p
    library.xkb_context_unref.argtypes = [ctypes.c_void_p]
    library.xkb_keymap_new_from_names.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    library.xkb_keymap_new_from_names.restype = ctypes.c_void_p
    library.xkb_keymap_unref.argtypes = [ctypes.c_void_p]
    context = library.xkb_context_new(0)
    if not context:
        return 2  # Never pass a null context to keymap_new (the observed SIGSEGV).
    keymap = library.xkb_keymap_new_from_names(context, None, 0)
    if keymap:
        library.xkb_keymap_unref(keymap)
    library.xkb_context_unref(context)
    return 0 if keymap else 3


if len(sys.argv) == 3 and sys.argv[1] == '--probe':
    raise SystemExit(probe(sys.argv[2]))

source = Path('/usr/share/X11/xkb')
if not ctypes.util.find_library('xkbcommon') or not source.is_dir():
    raise SystemExit('Native XKB regression requires libxkbcommon and xkb-data')
with tempfile.TemporaryDirectory(prefix='arch-xkb-native-') as temporary:
    root = Path(temporary)
    target = root/'usr/share/xkeyboard-config-2'
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)
    link = root/'usr/share/X11/xkb'
    link.parent.mkdir()
    # Use a unique guest target so no matching host path can accidentally satisfy it.
    target = target.rename(target.with_name('archohall-test-keyboard-data'))
    link.symlink_to('/usr/share/archohall-test-keyboard-data')
    broken = subprocess.run([sys.executable, __file__, '--probe', str(link)], capture_output=True)
    assert broken.returncode in (2, 3), f'Broken XKB path did not fail safely: {broken.returncode}'
    # Same lexical operation used by the upstream atomic symlink repair.
    staged = link.with_suffix('.portal-tmp')
    staged.symlink_to('../archohall-test-keyboard-data')
    staged.replace(link)
    fixed = subprocess.run([sys.executable, __file__, '--probe', str(link)], capture_output=True)
    assert fixed.returncode == 0, fixed.stderr.decode(errors='replace')
print('Native Linux XKB broken-link rejection and repaired default keymap: PASS')
