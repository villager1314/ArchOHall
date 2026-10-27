#!/usr/bin/env python3
"""Bundle managed guest files separately from the imported Linux rootfs."""
import subprocess
import sys
import zipfile
from pathlib import Path

REPO=Path(__file__).resolve().parent.parent


def build(destination):
    subprocess.run([sys.executable,str(REPO/'android/host-bridge/generate_tiles.py')],check=True)
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    source=REPO/'rootfs'
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((source/'usr/local').rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts: continue
            relative=path.relative_to(source).as_posix()
            info=zipfile.ZipInfo(relative,(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o100755 if relative.startswith('usr/local/bin/') else 0o100644)<<16
            archive.writestr(info,path.read_bytes())


if __name__=='__main__':
    build(sys.argv[1])
