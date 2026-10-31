#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
source, upstream, output = map(lambda value: Path(value).resolve(), sys.argv[1:])
output.mkdir(parents=True, exist_ok=True)
probe = json.loads((here / 'upstream-probe.json').read_text())
results = []
for record in probe['results']:
    patch = upstream / 'debian/patches' / record['patch']
    if hashlib.sha256(patch.read_bytes()).hexdigest() != record['sha256']:
        raise SystemExit('Upstream patch hash mismatch: ' + patch.name)
    run = subprocess.run(['patch', '--batch', '--forward', '-p1', '-i', str(patch)],
                         cwd=source, capture_output=True, text=True)
    (output / (patch.name + '.log')).write_text(run.stdout + run.stderr)
    results.append({'patch': patch.name, 'exit': run.returncode})
    # Known partially applied legacy hunks are retained for compiler diagnostics.
    # This is not a successful source-port or device-validation assertion.
    if run.returncode != record['exit']:
        raise SystemExit('Unexpected upstream patch result: ' + patch.name)
for patch in sorted((here / 'patches').glob('*.patch')):
    run = subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-i', str(patch)],
                         cwd=source, capture_output=True, text=True)
    (output / (patch.name + '.log')).write_text(run.stdout + run.stderr)
    if run.returncode:
        raise SystemExit('Port adaptation failed: ' + patch.name)
(output / 'source-port-status.json').write_text(json.dumps({
    'upstream_results': results, 'source_port_complete': False,
    'device_validation': False,
    'remaining_rejects': [str(p.relative_to(source)) for p in source.rglob('*.rej')],
}, indent=2) + '\n')
print('Prepared diagnostic source tree; compilation determines next errors.')
