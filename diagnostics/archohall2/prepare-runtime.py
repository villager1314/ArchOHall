#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path
base, output = map(Path, sys.argv[1:])
archive = base/'archohall-arch-mobile-experimental.tar.zst'
h = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
records = (base/'SHA256SUMS').read_text().splitlines()
assert any(line.split()[0] == h and Path(line.split()[-1]).name == archive.name for line in records), 'Reused rootfs checksum mismatch'
output.write_text(json.dumps({
    'distribution':'arch-mobile',
    'version':'archohall2-arch-mobile-2026.10.31.1',
    'url':'https://github.com/villager1314/ArchOHall/releases/download/archohall2-runtime-20261031-1/'+archive.name,
    'sha256':h, 'compressed_bytes':archive.stat().st_size,
    'rootfs_workflow_run':41166047320,
    'kwin_workflow_run':41162670069,
    'device_validated':False,
}, indent=2)+'\n')
print('Verified reused runtime and wrote Arch manifest')
