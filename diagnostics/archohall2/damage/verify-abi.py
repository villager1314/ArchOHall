#!/usr/bin/env python3
"""Require the existing real KWin library to export/preempt the compiled hooks."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('kwin',type=Path);p.add_argument('component',type=Path);p.add_argument('output',type=Path)
a=p.parse_args()
def run(*args):return subprocess.check_output(list(args),text=True)
header=run('readelf','-h',str(a.kwin));shim_header=run('readelf','-h',str(a.component/'anland-damage-68.so'))
assert 'AArch64' in header and 'AArch64' in shim_header,'Both real KWin and component must be ARM64'
exports=run('readelf','--dyn-syms','--wide',str(a.kwin))
relocs=run('readelf','--relocs','--wide',str(a.kwin))
dynamic=run('readelf','--dynamic','--wide',str(a.kwin))
assert '(SYMBOLIC)' not in dynamic,'KWin binds internal functions locally'
needed=(a.component/'required-symbols.txt').read_text().splitlines()
records=[]
for name in needed:
    definitions=[line for line in exports.splitlines() if line.split() and line.split()[-1].split('@')[0]==name and ' UND ' not in line]
    assert definitions,f'Existing KWin does not export {name}'
    assert any(' DEFAULT ' in line for line in definitions),f'Non-interposable visibility: {name}'
    eligible=[line for line in relocs.splitlines() if name in line and ('JUMP_SLOT' in line or 'GLOB_DAT' in line)]
    assert eligible,f'No preemptible relocation for {name}; cannot claim this preload hooks real KWin'
    records.append({'symbol':name,'exported':True,'preemptible_relocations':len(eligible)})
report={'architecture':'aarch64','kwin':a.kwin.name,'hooks':records,'kwin_rebuilt':False,'runtime_verified':False}
a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
